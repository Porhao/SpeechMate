"""LoRA fine-tune of a Whisper model on data/train.csv, scored on data/dev.csv (plan §6).

    python scripts/train_lora.py openai/whisper-small 200   # F4 smoke test: 200 steps
    python scripts/train_lora.py <base model>              # F5 real run: 3 epochs

CSV columns: file_name,transcript,language,speaker,source; audio in data/clips/ (16 kHz mono, <= 30 s).
Each clip gets its own language token (en/ms), no prompt, and timestamp tokens; dev decoding
auto-detects the language and uses timestamp mode, the way the app (faster-whisper) runs.
"""
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jiwer
import soundfile as sf
import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    BitsAndBytesConfig, Seq2SeqTrainer, Seq2SeqTrainingArguments,
    WhisperForConditionalGeneration, WhisperProcessor,
)

ROOT = Path(__file__).resolve().parent.parent
MODEL = sys.argv[1] if len(sys.argv) > 1 else "openai/whisper-small"
STEPS = int(sys.argv[2]) if len(sys.argv) > 2 else 0   # > 0: smoke test, else epochs
QUANT = None   # None (bf16), "8bit" or "4bit" (needs bitsandbytes): only if bf16 runs out of memory (plan §9)
OUT = ROOT / "out" / "adapter"

processor = WhisperProcessor.from_pretrained(MODEL, task="transcribe")
TS0 = processor.tokenizer.convert_tokens_to_ids("<|0.00|>")   # timestamp tokens step by 0.02 s

# --- data ---------------------------------------------------------------
ds = load_dataset("csv", data_files={"train": str(ROOT / "data/train.csv"), "dev": str(ROOT / "data/dev.csv")},
                  keep_default_na=False)  # an empty transcript (silent clip) stays "", not NaN

def prepare(row):
    audio, sr = sf.read(ROOT / "data/clips" / row["file_name"], dtype="float32")
    assert sr == 16000 and audio.ndim == 1, f"{row['file_name']}: need 16 kHz mono"
    assert len(audio) <= 30 * sr, f"{row['file_name']}: over 30 s"   # Whisper would cut the audio, not the label
    features = processor.feature_extractor(audio, sampling_rate=sr).input_features[0]
    # Timestamp mode, like faster-whisper in the app (Mesolitica's model loops without it):
    # <|sot|><|lang|><|transcribe|> <|0.00|> text <|end|> <|eot|>
    tok = processor.tokenizer
    tok.set_prefix_tokens(language=row["language"], task="transcribe", predict_timestamps=True)
    ids = tok(row["transcript"]).input_ids
    if row["transcript"]:
        n = len(tok.prefix_tokens)
        # ponytail: one segment ending at the clip's end; trailing silence makes <|end|> late.
        # Use real segment times (e.g. from VAD) if timestamps drift after fine-tuning.
        end = TS0 + min(round(len(audio) / sr / 0.02), 1500)
        ids = ids[:n] + [TS0] + ids[n:-1] + [end, ids[-1]]
    return {"input_features": features, "labels": ids}

# num_proc=1 is required: set_prefix_tokens changes shared tokenizer state.
# Caches about 1.5 MB of features per clip; for the 107 h set use ds.set_transform instead.
ds = ds.map(prepare, remove_columns=ds["train"].column_names, num_proc=1)

@dataclass
class Collator:
    processor: Any
    decoder_start_token_id: int

    def __call__(self, feats):
        batch = self.processor.feature_extractor.pad(
            [{"input_features": f["input_features"]} for f in feats], return_tensors="pt")
        batch["input_features"] = batch["input_features"].to(torch.bfloat16)  # match the model for generate()
        lab = self.processor.tokenizer.pad([{"input_ids": f["labels"]} for f in feats], return_tensors="pt")
        lab_ids = lab["input_ids"].masked_fill(lab.attention_mask.ne(1), -100)
        if (lab_ids[:, 0] == self.decoder_start_token_id).all().cpu().item():
            lab_ids = lab_ids[:, 1:]  # the model prepends it again
        batch["labels"] = lab_ids
        return batch

# --- model --------------------------------------------------------------
kwargs = {"torch_dtype": torch.bfloat16}
if QUANT:
    kwargs["quantization_config"] = (
        BitsAndBytesConfig(load_in_8bit=True) if QUANT == "8bit" else
        BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    )
    kwargs["device_map"] = {"": 0}   # not "auto": on 8 GB it can quietly offload layers to CPU
model = WhisperForConditionalGeneration.from_pretrained(MODEL, **kwargs)
model.config.use_cache = False
model.generation_config.language = None      # auto-detect during dev eval, like the app
model.generation_config.task = "transcribe"
model.generation_config.return_timestamps = True   # same mode as training and the app
model.generation_config.forced_decoder_ids = None

if QUANT:
    model = prepare_model_for_kbit_training(model)
else:
    model.enable_input_require_grads()

model = get_peft_model(model, LoraConfig(
    r=32, lora_alpha=64, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "out_proj"],
))
model.print_trainable_parameters()

# --- metrics ------------------------------------------------------------
def norm(t):
    t = re.sub(r"[^\w\s']", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()

def compute_metrics(pred):
    ids, lab = pred.predictions, pred.label_ids
    pad = processor.tokenizer.pad_token_id
    ids[ids == -100] = pad   # the eval loop pads predictions across batches with -100
    lab[lab == -100] = pad
    hyp = [norm(x) for x in processor.batch_decode(ids, skip_special_tokens=True)]
    ref = [norm(x) for x in processor.batch_decode(lab, skip_special_tokens=True)]
    pairs = [(r, h) for r, h in zip(ref, hyp) if r]   # silent clips are scored separately
    for r, h in pairs[:3]:
        print(f"\n  ref: {r}\n  hyp: {h}")
    return {
        "wer": jiwer.wer([r for r, _ in pairs], [h for _, h in pairs]) if pairs else 0.0,
        "silent_words": sum(len(h.split()) for r, h in zip(ref, hyp) if not r),   # must stay 0
    }

# --- train --------------------------------------------------------------
args = Seq2SeqTrainingArguments(
    output_dir=str(OUT),
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    per_device_eval_batch_size=4,
    learning_rate=3e-4,
    warmup_steps=min(50, STEPS // 10) if STEPS else 50,
    max_steps=STEPS or -1,
    num_train_epochs=3,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},  # reentrant drops LoRA grads in checkpointed layers
    eval_strategy="steps" if STEPS else "epoch",
    eval_steps=STEPS // 2 if STEPS else None,
    save_strategy="no" if STEPS else "epoch",
    predict_with_generate=True,
    generation_max_length=225,
    logging_steps=10,
    remove_unused_columns=False,
    label_names=["labels"],
    report_to="none",
)

trainer = Seq2SeqTrainer(
    model=model, args=args,
    train_dataset=ds["train"], eval_dataset=ds["dev"],
    data_collator=Collator(processor, model.config.decoder_start_token_id),
    compute_metrics=compute_metrics,
)
print("dev before training:", trainer.evaluate())
t = time.time()
trainer.train()
print(f"trained {time.time() - t:.0f} s | peak VRAM {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB")
model.save_pretrained(OUT)
processor.save_pretrained(OUT)
