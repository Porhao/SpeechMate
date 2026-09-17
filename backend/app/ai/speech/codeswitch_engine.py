"""
Code-switching ASR — Mesolitica's wav2vec2-xls-r-300m-mixed, the model
malaya_speech.stt.huggingface() itself wraps
(https://huggingface.co/mesolitica/wav2vec2-xls-r-300m-mixed). Trained on
Malay + Singlish + Mandarin-mixed speech (WER 0.132 / CER 0.048 per the
model card), specifically for the case generic Whisper handles worst:
code-switched Malaysian speech.

Loaded straight through `transformers` + PyTorch — both already project
dependencies — rather than installing the full malaya-speech package, which
would additionally require TensorFlow just to reach this same checkpoint.
Confirmed against the actual repo: it ships `pytorch_model.bin`, so the
PyTorch path is native, not a conversion.

This is a CTC model: one forward pass over the whole clip, greedy-decoded.
No beam search / language model rescoring — malaya_speech's own numbers
above are for the LM-rescored variant, so treat this path's raw output as a
touch noisier than that WER figure until an LM is added on top.
"""

from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

MODEL_ID = "mesolitica/wav2vec2-xls-r-300m-mixed"
SAMPLE_RATE = 16_000  # fixed by the model's preprocessor_config.json


@lru_cache(maxsize=1)
def _processor() -> Wav2Vec2Processor:
    return Wav2Vec2Processor.from_pretrained(MODEL_ID)


@lru_cache(maxsize=1)
def _model() -> Wav2Vec2ForCTC:
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID)
    model.eval()
    return model


@dataclass
class CodeSwitchResult:
    text: str
    engine: str = "mesolitica/wav2vec2-xls-r-300m-mixed"


def transcribe(audio: np.ndarray, sample_rate: int) -> CodeSwitchResult:
    """audio: mono float32 waveform. Caller is responsible for resampling to
    SAMPLE_RATE (see pipeline.py, which uses librosa for this) — resampling
    here would make every call pay librosa's import/JIT cost even when the
    audio's already at the right rate.
    """
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"audio must be pre-resampled to {SAMPLE_RATE} Hz, got {sample_rate}")

    processor = _processor()
    inputs = processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True)

    with torch.no_grad():
        logits = _model()(inputs.input_values).logits

    predicted_ids = torch.argmax(logits, dim=-1)
    text = processor.batch_decode(predicted_ids)[0].strip()
    return CodeSwitchResult(text=text)
