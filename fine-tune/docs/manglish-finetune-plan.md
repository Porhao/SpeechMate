# Fine-Tuning Plan: Your Own Manglish Speech Model (8 GB VRAM)

Companion to `docs/manglish-transcription-spec.md`. Status: draft v2, 2 Oct 2026; phase status updated 8 Oct 2026 (§3).
Goal: fine-tune an open Whisper-family model on Manglish so SpeechMate transcribes your users better than **the model SpeechMate already ships**, and you own the resulting weights.

**Read this first:** the code blocks in this file are the original skeleton. The tested versions are in `fine-tune/scripts/` (`prepare_public.py`, `train_lora.py`, `export.py`, `eval_finetune.py`); results are in `fine-tune/RESULTS.md`. Library versions change (`transformers`, `peft`, `bitsandbytes`), so expect to fix small API differences. Everything is gated on measured results, not on hope.

**v2 changes:** this version was checked against the repo. The baseline is now Mesolitica turbo-v3, not vanilla Whisper. The language token is auto-detected, not forced. The prompt is the same in training and inference. Speed is measured on CPU int8, the way the app runs. The plan reuses `bench_stt.py` and `convert_whisper.sh`. The training script has fixes for bf16, `device_map`, the 30 s limit, and empty metrics.

---

## 1. Principles

1. **Fine-tune, don't train from scratch.** Start from a pretrained model and adapt it.
2. **The baseline is what SpeechMate ships today:** Mesolitica `Malaysian-whisper-large-v3-turbo-v3`, with CTranslate2 int8 on CPU, auto-detected language and the app's prompt. Its WER is 7.9% overall (`docs/benchmarks/stt-benchmark-2026-09-30.md`). Beating vanilla Whisper is not enough, because vanilla Whisper translates one language into the other with either fixed token.
3. **Measure before and after** on a test set the model never sees. If the fine-tune doesn't beat the baseline, you don't ship it.
4. **Data quality beats data quantity.** A few hours of correct transcripts from varied speakers beat many hours of wrong ones.
5. **Preserve what the model already does well:** silence handling, noisy audio, plain English, plain Malay. Fine-tunes can quietly damage these (a Malaysian fine-tune did exactly this in the hallucination paper cited in the spec).
6. **Only use data you have the rights and consent to use.**

---

## 2. Choices made for an 8 GB GPU (RTX 4060 Laptop, WSL2)

| Decision | Choice | Why |
|---|---|---|
| Method | LoRA (adapter weights only) | Full fine-tuning of a large model will not fit in 8 GB |
| Base model | **Decided in F0 by the licence check.** If the Mesolitica licence allows derivatives, use `mesolitica/Malaysian-whisper-large-v3-turbo-v3`. If it doesn't, use `openai/whisper-large-v3-turbo`. | Fine-tuning the model you ship is the best chance of beating it. A LoRA on vanilla turbo trained on 5-10 h must close a big gap first. |
| Smoke-test model | `openai/whisper-small` | Fast to iterate; proves the pipeline works |
| Precision | **bf16 first** (turbo is about 809M parameters, about 1.6 GB in bf16). Use 8-bit or 4-bit only if bf16 runs out of memory. | The 4060 (Ada) supports bf16. That avoids fp16 loss-scaling problems and the bitsandbytes setup. |
| Language token | **Auto-detect at inference.** In training, give each clip the token of its main language (`en` or `ms`). | Forcing one token makes the model translate: US English came out as Malay (`stt-benchmark-2026-10-01.md`). Per-clip tokens match how Whisper was trained and how the app runs. |
| Prompt | **Train and infer the same way.** The default is to train with no prompt and run the fine-tuned model with `initial_prompt=None`. | The app sends `VERBATIM_PROMPT` on every path. A model trained without it and tested with it is not the model you measured. The style-guide labels teach verbatim fillers directly. |
| Timestamp mode | **Train with timestamp tokens** (`<|0.00|> text <|end|>`) and evaluate with `return_timestamps=True` | faster-whisper decodes in timestamp mode by default. Mesolitica's model only works in that mode: without it, it never stops and loops ("5.5.5.5..."). This was found in the F4 smoke test. |
| Final runtime | faster-whisper (CTranslate2), **int8 on CPU**, 8 threads | This is how the app runs in Docker (`asr._whisper_model`) |

**Licences:** Whisper weights are MIT and Qwen3-ASR is Apache-2.0. Mesolitica's model card shows no licence. This affects both **shipping** the model (the app's current default) and **fine-tuning** it, so settle it once in F0: ask Mesolitica, or treat the model as unusable for both. Write the answer down in `RESULTS.md`.

---

## 3. Phases

| Phase | What | Done when | Status (8 Oct) |
|---|---|---|---|
| F0 | Environment, licences, ethics | `nvidia-smi` shows the GPU. Packages install. Mesolitica licence answered (this picks the base model). Data licences written down. **University ethics approval** for recording people. WSL RAM raised (see §9). | **Partly.** Environment done (`.venv`, `.venv-app`, `.venv-convert`). Licence question and ethics approval still open. |
| F1 | Finish the bake-off (spec M1-M3) | Mostly done: `bench_stt.py` plus three reports in `docs/benchmarks/`. **Remaining: M1, real recordings.** All English and Manglish clips so far are synthetic TTS. | **Partly.** Public bake-off done; real recordings (M1) not started. |
| F2 | Collect and clean data | 5+ hours of verified clips, speaker-split train/dev/test | **Partly.** Recording kit ready (`STYLE_GUIDE.md`, `RECORDING_PROMPTS.md`, consent form). Public substitute: 10.3 h (`scripts/prepare_public.py`). Own recordings not started. |
| F3 | Build the manifest and the dataset | `data/` loads with `datasets`; test set locked; no clip over 30 s | **Done for public data** (`data/train.csv`, `dev.csv`, split by voice). |
| F4 | Smoke test on `whisper-small` | 200 steps run end to end; loss drops; no crashes | **Done** (whisper-small, vanilla turbo, Mesolitica; `RESULTS.md`). |
| F5 | Real training run | Adapter saved; dev WER logged every epoch | **Done on public data.** Mesolitica base, lr 1e-4, dev WER 19.5% → 4.1% (`out/adapter/`). |
| F6 | Evaluate vs the shipped baseline | Report with every metric in §7 | **Partly.** 400 public clips: English 9.4% → 6.7%, mixed 14.5% → 6.7%, silence 0/10 (`docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`). Real speakers and noisy real speech still needed. |
| F7 | Merge and convert | `/models/ct2/<name>` loads in faster-whisper (via `convert_whisper.sh`) | **Done** (`scripts/export.py` → `out/ct2/`). |
| F8 | Plug into SpeechMate | `WHISPER_MODEL_SIZE` switch; code-switch routing and prompt handled (§8); A/B against baseline | Not started: waits on F6 with real speakers and the licence answer. |
| F9 | Improvement loop | Tap-to-correct data feeds the next training round | Not started. |

**Do F1 (M1) before anything else.** A real test set is worth more than any fine-tune. Only fine-tune if the shipped model clearly fails on it.

---

## 4. Data plan

### 4.1 Sources

| Source | Use | Notes |
|---|---|---|
| **Your own recordings** (you, friends, target users) | Train, dev and test | Best match to real use. Needs **informed consent** from every speaker and **ethics approval** first. |
| **Tap-to-correct logs** from SpeechMate | Train (later rounds) | Store audio only with explicit opt-in. Delete on request. |
| **Semisupervised Manglish set** (about 107 h, CC BY 4.0, Mesolitica, listed on Malaya-Speech docs) | Extra training, after filtering (§4.6) | Transcripts are **model-written**. Never use as test data. Keep attribution. |
| **Synth-Manglish** (`emhaihsan/Synth-Manglish`, 2,457 clips, about 7 h, CC BY 4.0) | Training (in use, `scripts/prepare_public.py`) | Synthetic TTS voices, so it adds Manglish vocabulary and code-switching but not real accents or fillers. Keep attribution. |
| **FLEURS** `ms_my` / `en_us` (CC BY 4.0) | Guard data (in use) | Real Malay and English speakers. The test split stays reserved for the STT benchmark. |
| IMDA National Speech Corpus (Singapore Open Data Licence) | Optional accented-English replay | Singaporean, not Malaysian. |
| MagicHub ASR-MalCSC (CC BY-NC-ND 4.0) | **Avoid for fine-tuning** | "No derivatives" may forbid it; it is also non-commercial. Fine for evaluation only if you are comfortable with the terms. |

### 4.2 How much

| Hours of verified speech | Expectation |
|---|---|
| 1-3 | Pipeline test only. Likely overfits. |
| 5-10 | Can show a measurable gain on a narrow speaker group |
| 20-50 | A more solid target |

Speaker variety matters as much as hours. Aim for **10 or more speakers**, including different accents, ages, and levels of Malay-English mixing. A model trained on three voices will memorise them.

### 4.3 Recording and labelling rules

- 16 kHz mono WAV, clips of 3-30 seconds. Split on pauses; never cut mid-word.
- **`prepare_data.py` rejects any clip over 30 s.** Whisper's feature extractor cuts audio at 30 s but the label keeps the full text, which teaches the model to hallucinate.
- Record on the devices users will actually use (laptop mic, phone), including some background noise.
- Write a one-page **transcription style guide** before labelling and follow it strictly:
  - Keep fillers ("um", "uh", "lah", "kan") exactly as spoken.
  - Spell common Malay words one agreed way (e.g. "takde" vs "tak ada": choose one).
  - Particles: decide whether they are attached ("kenyanglah") or separate ("kenyang lah"). The app's particle counter currently misses the attached form (`stt-benchmark-2026-10-02.md`).
  - Do not translate, do not fix grammar.
  - Numbers: write as spoken, or as digits, but pick one.
  - Punctuation and capitalisation: light and consistent (the scoring step lowercases and strips it anyway).
- Record each clip's **main language** (`en` or `ms`) in the manifest. Training uses it as the clip's language token.
- Labelling is slow: expect about 5-10x real time, so 5 h of audio is roughly 25-50 h of work. A common trick is to pre-fill with the baseline model's output and correct it, but this can anchor you to the model's mistakes, so listen to every clip fully.
- Have a second person re-check a random 10% to catch systematic errors.

### 4.4 Guard data (do not skip)

Mix these into training so the model keeps its existing strengths:

- Plain English and plain Malay clips (about 20-30% of the mix)
- Noisy clips
- **Silent or near-silent clips with an empty transcript** (about 3-5%), so it keeps learning to output nothing

### 4.5 Splits

- **Test set:** 10-15% of speakers, chosen first and **locked**. No clip or speaker from it ever appears in training. Do not tune on it.
- **Dev set:** another 10% of speakers, used for choosing epochs and learning rate.
- **Train:** the rest.
- Split by **speaker**, not by clip, otherwise the test score is inflated.

### 4.6 Filtering the pseudo-labelled 107 h set

The set comes with model-written transcripts. The filter checks those **provided labels**, not the models against each other.

1. Run two different models over the clips, for example vanilla Whisper and Qwen3-ASR.
2. Keep a clip only if **both** model outputs are close to the provided label (WER against the label below about 10%). The provided label stays as the training target.
3. Hand-check a random sample of 100 kept clips. If more than about 10% are wrong, tighten the filter or drop the set.
4. Use the kept clips only for training, never for dev or test.

---

## 5. Repo layout

```
fine-tune/
  data/
    raw/                 # original recordings (never edited)
    clips/               # processed 16 kHz mono WAV, 3-30 s
    train.csv  dev.csv  test.csv     # columns: file_name,transcript,language,speaker,source
  scripts/
    prepare_data.py      # resample, trim, reject >30 s, build CSVs split by speaker
    train_lora.py        # training (section 6)
    export.py            # merge LoRA into the base (section 8)
  out/
    adapter/  merged/
  STYLE_GUIDE.md         # transcription rules from 4.3
  RESULTS.md             # table of every run: settings, dev WER, test WER; licences
```

The repo already has the following, so reuse them rather than writing new versions:
- **Evaluation:** `backend/scripts/benchmark/bench_stt.py`. Extend it to read `test.csv` and report the extra metrics in §7.
- **Conversion:** `backend/scripts/convert_whisper.sh` converts to CTranslate2 int8 in the model-cache volume.

Keep `RESULTS.md` honest: one row per run, including the failed ones.

---

## 6. Training script

**The tested version is `fine-tune/scripts/train_lora.py`** (F4 smoke tests passed). It supersedes the skeleton below, which lacks timestamp-mode labels (§2).

Install (versions will differ; use a fresh virtual environment):

```
pip install torch transformers datasets peft accelerate bitsandbytes jiwer soundfile librosa
```

`scripts/train_lora.py`:

```python
import re
import sys
from dataclasses import dataclass
from typing import Any

import torch
import jiwer
from datasets import load_dataset, Audio
from transformers import (
    WhisperForConditionalGeneration, WhisperProcessor, BitsAndBytesConfig,
    Seq2SeqTrainer, Seq2SeqTrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Smoke test: openai/whisper-small. Real run: the base chosen in F0, e.g.
# mesolitica/Malaysian-whisper-large-v3-turbo-v3 or openai/whisper-large-v3-turbo.
MODEL = sys.argv[1] if len(sys.argv) > 1 else "openai/whisper-small"
QUANT = None         # None (bf16), "8bit" or "4bit": only if bf16 runs out of memory (section 9)
OUT = "out/adapter"

processor = WhisperProcessor.from_pretrained(MODEL, task="transcribe")

# --- data ---------------------------------------------------------------
ds = load_dataset("csv", data_files={"train": "data/train.csv", "dev": "data/dev.csv"})
ds = ds.map(lambda r: {"audio": "data/clips/" + r["file_name"]})
ds = ds.cast_column("audio", Audio(sampling_rate=16000))

def prepare(batch):
    audio = batch["audio"]
    assert len(audio["array"]) <= 30 * 16000, batch["audio"]["path"]   # prepare_data.py should have caught it
    batch["input_features"] = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"]).input_features[0]
    # Per-clip language token (en/ms), matching auto-detect at inference.
    # No prompt: the fine-tuned model also runs with initial_prompt=None (section 8).
    processor.tokenizer.set_prefix_tokens(language=batch["language"], task="transcribe")
    batch["labels"] = processor.tokenizer(batch["transcript"] or "").input_ids
    return batch

# num_proc=1 is required: set_prefix_tokens changes shared tokenizer state.
# Stores about 1.5 MB of features per clip; for the 107 h set use ds.set_transform(prepare) instead.
ds = ds.map(prepare, remove_columns=ds["train"].column_names, num_proc=1)

@dataclass
class Collator:
    processor: Any
    decoder_start_token_id: int

    def __call__(self, feats):
        inputs = [{"input_features": f["input_features"]} for f in feats]
        batch = self.processor.feature_extractor.pad(inputs, return_tensors="pt")
        labels = [{"input_ids": f["labels"]} for f in feats]
        lab = self.processor.tokenizer.pad(labels, return_tensors="pt")
        lab_ids = lab["input_ids"].masked_fill(lab.attention_mask.ne(1), -100)
        if (lab_ids[:, 0] == self.decoder_start_token_id).all().cpu().item():
            lab_ids = lab_ids[:, 1:]
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
    t = t.lower()
    t = re.sub(r"[^\w\s']", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def compute_metrics(pred):
    ids = pred.predictions
    lab = pred.label_ids
    lab[lab == -100] = processor.tokenizer.pad_token_id
    hyp = [norm(x) for x in processor.batch_decode(ids, skip_special_tokens=True)]
    ref = [norm(x) for x in processor.batch_decode(lab, skip_special_tokens=True)]
    pairs = [(r, h) for r, h in zip(ref, hyp) if r]   # skip silent clips for WER
    silent_words = sum(len(h.split()) for r, h in zip(ref, hyp) if not r)
    wer = jiwer.wer([p[0] for p in pairs], [p[1] for p in pairs]) if pairs else 0.0
    return {"wer": wer, "silent_words": silent_words}

# --- train --------------------------------------------------------------
args = Seq2SeqTrainingArguments(
    output_dir=OUT,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    per_device_eval_batch_size=2,
    learning_rate=3e-4,
    warmup_steps=50,
    num_train_epochs=3,
    bf16=True,
    gradient_checkpointing=True,
    eval_strategy="epoch",
    save_strategy="epoch",
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
trainer.train()
model.save_pretrained(OUT)
processor.save_pretrained(OUT)
```

### 6.1 Smoke test before a real run

1. Use a tiny dataset (50 clips) and `max_steps=200` instead of epochs.
2. Watch `nvidia-smi` for peak VRAM. If it nears 8 GB, work down section 9.
3. Confirm loss decreases and that decoded dev output looks like text, not garbage.
4. Time 200 steps and extrapolate to the full run so you know the cost before committing.

### 6.2 Settings to tune (one change per run)

| Setting | Start | Try |
|---|---|---|
| Learning rate | 3e-4 | 1e-4 (if dev WER is unstable, and for a Mesolitica base, which is already tuned), 5e-4 (if learning is slow) |
| LoRA rank `r` | 32 | 16 (less overfitting), 64 (more capacity) |
| Epochs | 3 | Stop when dev WER stops improving |
| Dropout | 0.05 | 0.1 if it overfits |

Warning signs: training loss keeps falling while dev WER rises (overfitting; stop earlier or add data), dev WER jumps around (lower the learning rate), output repeats words in loops (check silent clips and data labels), `silent_words` above zero (more empty-transcript clips).

---

## 7. Evaluation (extend `backend/scripts/benchmark/bench_stt.py`)

Run both models on the locked test set through the app's own `whisper_segments()`, with identical normalisation:
- **Baseline:** the shipped model with the shipped settings: CT2 int8 on CPU, 8 threads, auto-detected language, `VERBATIM_PROMPT`.
- **Fine-tune:** the converted model with its own settings: CT2 int8 on CPU, auto-detected language, `initial_prompt=None` (or the prompt, if you trained with it).

Report all of these:

| Metric | How | Must |
|---|---|---|
| Overall WER | `jiwer` on normalised text | Beat the baseline by a clear margin (suggest at least 10% relative; decide your own threshold up front) |
| English-word accuracy | Tag reference words `en`/`ms`; score each group separately | Not worse than baseline |
| Malay-word accuracy | Same | Better than baseline |
| Language preservation | Count clips where English words come out as Malay or the reverse | Not worse than baseline |
| Filler retention | Fraction of reference fillers present | Not worse than baseline |
| Silence safety | Words produced on silent clips | **Zero** |
| Noise robustness | WER on the noisy subset | Not worse than baseline |
| Speed | Seconds per 5 s turn, CPU int8, 8 threads (as in the existing benchmarks) | Within your latency budget (baseline is about 2.3-2.7 s) |

Report per-speaker WER too. If one speaker is far worse, the model has not generalised.

---

## 8. Export and use

Merge the adapter into the **unquantised** base model. Do not merge into an 8-bit or 4-bit one.

`scripts/export.py`:

```python
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from peft import PeftModel

BASE = "mesolitica/Malaysian-whisper-large-v3-turbo-v3"   # same base you trained on
base = WhisperForConditionalGeneration.from_pretrained(BASE, torch_dtype=torch.float16)
merged = PeftModel.from_pretrained(base, "out/adapter").merge_and_unload()
merged.save_pretrained("out/merged")
WhisperProcessor.from_pretrained(BASE).save_pretrained("out/merged")
```

To convert, use `backend/scripts/convert_whisper.sh`. It writes CT2 int8 to `/models/ct2/<name>` in the `speechmate_model_cache` volume. The script currently only mounts that volume, so a local `out/merged` folder isn't visible inside its container. In F7, either add a `-v` mount for a local folder or copy `out/merged` into the volume first.

To plug it into SpeechMate (F8):
- Set `WHISPER_MODEL_SIZE=/models/ct2/<name>`. The app keeps its CPU int8 runtime.
- **Code-switch routing:** `_transcribe_local` sends clips Whisper isn't sure are English to the wav2vec2 code-switch model, unless `is_malaysian_model()` is true. A Manglish fine-tune should skip that route too, either by having `malaysian-whisper` in its folder name or by an explicit setting.
- **Prompt:** `whisper_segments()` always sends `VERBATIM_PROMPT`. If you trained without it, add a setting that turns it off for this model.
- **Language:** leave `STT_LANGUAGE` empty (auto-detect), as trained.
- Keep the baseline selectable through `WHISPER_MODEL_SIZE` so you can A/B and roll back instantly.

---

## 9. If 8 GB is not enough

**WSL RAM first:** WSL had 7.6 GB of RAM on the benchmark machine. Loading turbo plus the dataset can exhaust it before VRAM runs out. Raise `memory=` under `[wsl2]` in `%UserProfile%\.wslconfig`.

Then, in order of preference:

1. Lower the batch size to 1 and raise gradient accumulation.
2. Trim training clips to 20 seconds or less.
3. Quantise the base: `QUANT = "8bit"`, then `QUANT = "4bit"` (QLoRA, nf4).
4. Drop to `whisper-medium` or `whisper-small`.
5. Use a free Kaggle or Colab GPU (about 16 GB, session-limited). Upload only data you have the rights to share, save checkpoints often, and download the adapter at the end.

---

## 10. Risks

| Risk | Sign | Response |
|---|---|---|
| Baseline is too strong | The fine-tune beats vanilla but not the shipped Mesolitica model | Expected with a small dataset on a vanilla base. Fine-tune on Mesolitica if the licence allows, or collect more data. |
| Overfitting to a few voices | Great train score, poor test score on new speakers | More speakers, lower rank, fewer epochs |
| Forgetting plain English/Malay | Baseline beats you on non-Manglish clips | Raise the share of guard data |
| Translating instead of transcribing | English comes out as Malay or the reverse | Check the per-clip language tags; keep auto-detect |
| Hallucination on silence | Text on empty clips | More empty-transcript clips; keep VAD on |
| Label noise | Inconsistent spellings, wrong words | Style guide; second-person review of 10% |
| Transcribing the labeller's habits | Model copies a labeller's quirks | Use 2+ labellers; review samples |
| Out of memory | CUDA OOM error or a killed WSL process | Section 9 |
| Privacy, consent or ethics problem | User audio collected without clear opt-in or approval | Ethics approval before F2; opt-in only; document retention; deletion on request |
| Licence problem | Data or base model licence forbids use | Record every licence in `RESULTS.md` before training |

---

## 11. Go / no-go

Ship the fine-tune only if **all** of these hold on the locked test set, compared with **the shipped baseline**:

- Overall WER better than the baseline by your pre-set margin
- Silence safety still zero
- Noise robustness, English-word accuracy and language preservation not worse than baseline
- Speed (CPU int8) within your latency budget
- Gains hold across speakers, not just one
- Data and base-model licences are clear for your intended use

If it fails, keep the baseline, look at the error types, and gather targeted data (for example more clips of the words it gets wrong) before the next round.

---

## 12. Suggested schedule (rough; depends heavily on ethics approval and labelling time)

| Week | Work |
|---|---|
| 1 | F0: licences, ethics application, environment, style guide |
| 2-3 | F1/F2: record real clips, lock the test set, run the shipped baseline on it (spec M1). Then label 3-5 h of training data (about 25-50 h of work). |
| 4 | F3-F5: manifest, smoke test on `whisper-small`, first real run |
| 5 | F5-F6: turbo LoRA run, evaluate against the shipped baseline |
| 6 | F7-F8: export, plug into SpeechMate, A/B |
| Ongoing | F9: add corrected clips, retrain when you have a meaningful batch (for example +5 hours) |

Ethics approval and labelling are usually the slowest steps. Start both first.

---

## 13. How to use this file

Give your coding assistant this file together with `docs/manglish-transcription-spec.md` and ask for one phase at a time, for example: "Implement F3: write `scripts/prepare_data.py` that builds train/dev/test CSVs split by speaker, following section 4 of fine-tune/docs/manglish-finetune-plan.md." Commit after each phase.

---

## 14. Sources

In this repo:
- `docs/benchmarks/stt-benchmark-2026-09-30.md`: model choice; Mesolitica turbo-v3 at 7.9% WER; vanilla Whisper translating with either fixed token
- `docs/benchmarks/stt-benchmark-2026-10-01.md`: forced `ms` translating English; auto-detect adopted
- `docs/benchmarks/stt-benchmark-2026-10-02.md`: shared verbatim prompt; particle spelling

From the earlier research:
- Code-switching ASR fine-tuning evidence (Singapore languages incl. Malay-English): https://arxiv.org/html/2506.14177
- Whisper adaptation on code-switched data (Mandarin-English): https://arxiv.org/pdf/2311.17382
- Malaysian fine-tunes degrading noise and other-language performance: https://arxiv.org/html/2609.32560
- Mesolitica Malaysian-STT-Whisper dataset (no licence stated): https://huggingface.co/datasets/mesolitica/Malaysian-STT-Whisper
- Malaya-Speech datasets (incl. semisupervised Manglish, CC BY 4.0): https://malaya-speech.readthedocs.io/en/stable/Dataset.html
- MagicHub ASR-MalCSC (CC BY-NC-ND 4.0): https://magichub.com/datasets/malay-conversational-speech-corpus/
- IMDA National Speech Corpus: https://www2.imda.gov.sg/NationalSpeechCorpus
- Qwen3-ASR (Apache-2.0): https://github.com/QwenLM/Qwen3-ASR
