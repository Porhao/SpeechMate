"""Local Malaysian text-to-speech: mesolitica/Malaysian-TTS-0.6B-v1.

A Qwen3-0.6B causal LM that writes DistilCodec audio tokens (IDEA-Emdoor/
DistilCodec-v1.0, 24 kHz, ~93 tokens per second of audio), trained on Malay
and English with natural code-switching. Open source and fully local — the
default narrator for the Ideal Presentation Agent.

- Fixed voices only (VOICES below): it does not clone the user's voice.
- One generate() call covers ~10 s of audio, so text is split into short
  chunks, synthesized one by one, and joined with a short pause.
- Runs on CPU (slowly) or on a CUDA GPU when one is available.
- The model card recommends normalizing text (numbers → words); digits are
  spelled out here for the simple cases a slide script contains.

Needs requirements-ml.txt (torch, transformers ≥ 4.51, distilcodec).
"""

import json
import logging
import re
import threading
import wave
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.services.live._ml import available

logger = logging.getLogger(__name__)

MODEL_ID = "mesolitica/Malaysian-TTS-0.6B-v1"
CODEC_REPO = "IDEA-Emdoor/DistilCodec-v1.0"
SAMPLE_RATE = 24000
CHUNK_MAX_CHARS = 140          # ≈ 20–25 words, comfortably under one generate() call
MAX_NEW_TOKENS = 1024          # ≈ 11 s of audio at 93 tokens/s
CHUNK_PAUSE_SEC = 0.25

# id → label (as shown in the frontend's narrator picker)
VOICES: dict[str, str] = {
    "husein": "Husein — Malaysian male",
    "idayu": "Idayu — Malaysian female",
    "haqkiem": "Haqkiem — Malaysian male",
    "singaporean": "Singaporean English",
    "singlish-speaker2050": "Singlish speaker 1",
    "singlish-speaker2202": "Singlish speaker 2",
    "DisfluencySpeech": "Conversational (natural disfluencies)",
}

# The model and codec aren't thread-safe; one synthesis at a time
_lock = threading.Lock()


def is_available() -> bool:
    return available("torch", "transformers", "distilcodec")


def unload() -> None:
    """Free the model's memory (~3.5 GB on CPU); it reloads from disk on next use."""
    import gc

    with _lock:
        _load.cache_clear()
    gc.collect()


def keep_loaded() -> bool:
    """On a GPU keep it warm; on CPU free it after each deck so the other models fit in RAM."""
    return _device() == "cuda"


def _device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=1)
def _load():
    import torch
    from distilcodec import DistilCodec
    from huggingface_hub import hf_hub_download
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = _device()
    logger.info("Loading %s + DistilCodec on %s…", MODEL_ID, device)
    config_path = hf_hub_download(CODEC_REPO, "model_config.json")
    ckpt_path = hf_hub_download(CODEC_REPO, "g_00204000")
    if device == "cuda":
        codec = DistilCodec.from_pretrained(
            config_path=config_path, model_path=ckpt_path, use_generator=True, is_debug=False
        )
    else:
        # DistilCodec.from_pretrained hard-codes CUDA, so build it and load the weights ourselves
        with open(config_path) as f:
            codec = DistilCodec(json.load(f))
        codec.device = torch.device("cpu")
        state = torch.load(ckpt_path, map_location="cpu")
        codec.generator.load_state_dict(state["generator"])
        codec.encoder.load_state_dict(state["encoder"])
        codec.quantizer.load_state_dict(state["quantizer"])
    codec.eval()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32
    ).to(device).eval()
    return tokenizer, model, codec


# ── Text preparation ────────────────────────────────────────────────────────

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _number_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    if n < 1000:
        rest = n % 100
        return _ONES[n // 100] + " hundred" + ("" if rest == 0 else " and " + _number_words(rest))
    if n < 1_000_000:
        rest = n % 1000
        return _number_words(n // 1000) + " thousand" + ("" if rest == 0 else " " + _number_words(rest))
    return " ".join(_ONES[int(d)] for d in str(n))


def normalize(text: str) -> str:
    text = re.sub(r"(\d+)%", lambda m: m.group(1) + " percent", text)
    text = re.sub(r"\d+", lambda m: _number_words(int(m.group(0))), text)
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, max_chars: int = CHUNK_MAX_CHARS) -> list[str]:
    """Split on sentence ends, then on commas, then on words, so each chunk fits one generation."""
    chunks: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", normalize(text)):
        parts = [sentence] if len(sentence) <= max_chars else re.split(r"(?<=[,;:])\s+", sentence)
        for part in parts:
            while len(part) > max_chars:
                cut = part.rfind(" ", 0, max_chars)
                cut = cut if cut > 0 else max_chars
                chunks.append(part[:cut].strip())
                part = part[cut:].strip()
            if part:
                chunks.append(part)
    return [c for c in chunks if re.search(r"\w", c)]


# ── Synthesis ───────────────────────────────────────────────────────────────

def _generate_chunk(text: str, speaker: str):
    import torch

    tokenizer, model, codec = _load()
    prompt = f"<|im_start|>{speaker}: {text}<|speech_start|>"
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs, max_new_tokens=MAX_NEW_TOKENS, temperature=0.7, do_sample=True, repetition_penalty=1.1
        )
    speech = tokenizer.decode(out[0]).split("<|speech_start|>")[-1].replace("<|endoftext|>", "")
    codes = [int(c) for c in re.findall(r"speech_(\d+)", speech)]
    if not codes:
        raise RuntimeError("The TTS model produced no speech tokens")
    # Same as codec.decode_from_codes(codes, minus_token_offset=False), which only runs on CUDA
    indices = torch.tensor(codes, dtype=torch.int64).view(1, 1, -1, 1).to(model.device)
    with torch.no_grad():
        audio = codec.generator(codec.quantizer.decode(indices=indices))
    return audio[0, 0].float().cpu().numpy()


def synthesize(text: str, out_wav: Path, speaker: str | None = None) -> Path:
    """Blocking — run via asyncio.to_thread. Writes a 24 kHz mono 16-bit WAV."""
    import numpy as np

    speaker = speaker if speaker in VOICES else settings.malaysian_tts_voice
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("Nothing to synthesize")

    pause = np.zeros(int(SAMPLE_RATE * CHUNK_PAUSE_SEC), dtype=np.float32)
    pieces = []
    with _lock:
        for chunk in chunks:
            pieces += [_generate_chunk(chunk, speaker), pause]
    audio = np.concatenate(pieces[:-1])
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return out_wav
