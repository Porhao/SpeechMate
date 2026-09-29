"""Pronunciation scoring with Wav2Vec2 (facebook/wav2vec2-base-960h) CTC confidence.

Word-level confidence is the mean CTC frame confidence over a proportional
time span per word (audio split evenly across the transcript's words), not a
true forced alignment (Montreal Forced Aligner is a much heavier dependency).
It's real inference on the real audio, with coarser word boundaries than
full forced alignment would give. The Malaysian-English accent allowance is
applied afterwards (language.adjust_pronunciation_for_accent).
"""

import logging
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_NAME = "facebook/wav2vec2-base-960h"
CORRECT_THRESHOLD = 75


@dataclass
class PronunciationResult:
    score: float                                   # 0–100
    word_scores: list[dict] = field(default_factory=list)  # [{word, score, is_correct}]
    incorrect_words: list[str] = field(default_factory=list)
    mispronunciation_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=1)
def _model():
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    logger.info("Loading Wav2Vec2 '%s' (CPU)…", MODEL_NAME)
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_NAME)
    model.eval()
    return Wav2Vec2Processor.from_pretrained(MODEL_NAME), model


def assess(wav_16k: Path, transcript: str) -> PronunciationResult | None:
    """Blocking — call via asyncio.to_thread. None if the audio or transcript is empty."""
    import numpy as np
    import torch

    from app.services.live.audio import MODEL_SAMPLE_RATE, load_wav_float

    words = transcript.split()
    waveform = load_wav_float(wav_16k)
    if not words or waveform.size == 0:
        return None

    processor, model = _model()
    inputs = processor(waveform, sampling_rate=MODEL_SAMPLE_RATE, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(inputs.input_values).logits
    frame_conf = torch.softmax(logits, dim=-1)[0].max(dim=-1).values.numpy()

    n_frames, n_words = len(frame_conf), len(words)
    word_scores, incorrect = [], []
    for i, w in enumerate(words):
        lo, hi = int(n_frames * i / n_words), int(n_frames * (i + 1) / n_words)
        span = frame_conf[lo:hi] if hi > lo else frame_conf[lo:lo + 1]
        s = round(min(max(float(np.mean(span)) * 100 if span.size else 50.0, 30.0), 99.0), 1)
        word_scores.append({"word": w, "score": s, "is_correct": s >= CORRECT_THRESHOLD})
        if s < CORRECT_THRESHOLD:
            incorrect.append(w)

    return PronunciationResult(
        score=round(sum(ws["score"] for ws in word_scores) / len(word_scores), 1),
        word_scores=word_scores,
        incorrect_words=incorrect,
        mispronunciation_count=len(incorrect),
    )
