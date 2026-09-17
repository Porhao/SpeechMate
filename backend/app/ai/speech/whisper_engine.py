"""
faster-whisper wrapper — the general-purpose / English-path ASR engine, and
also our language-ID signal (Whisper's own detector, run on the first chunk
of audio, decides whether a clip needs routing to the code-switching model
in pipeline.py — no separate language-ID model or dependency needed for that
routing decision).

Model is loaded once per process (lazy singleton) since constructing a
WhisperModel loads real weights — every route handler calling transcribe()
should share this instance rather than each building their own.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache

from faster_whisper import WhisperModel

# "small" balances accuracy and CPU latency reasonably for a live-ish coaching
# session; swap to "medium"/"large-v3" if accuracy matters more than latency
# and the deployment box has the RAM for it. int8 keeps CPU inference fast.
MODEL_SIZE = "small"
COMPUTE_TYPE = "int8"


@lru_cache(maxsize=1)
def _model() -> WhisperModel:
    return WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)


@dataclass
class WhisperResult:
    text: str
    language: str              # ISO 639-1, e.g. "en", "ms"
    language_probability: float
    duration: float = 0.0
    words: list[dict] = field(default_factory=list)  # populated only when word_timestamps=True


def transcribe(audio_path: str, word_timestamps: bool = False) -> WhisperResult:
    """Auto-detects language; does not force English. Only the first
    `language_detection_segments` chunk is used for the language guess
    (faster-whisper default), which is exactly what we want for a cheap
    routing signal in pipeline.py rather than a per-word answer.

    word_timestamps=True additionally returns per-word start/end times
    (needed for pause/articulation-rate analysis downstream in
    speech/fluency.py) at the cost of a slower decode.
    """
    segments, info = _model().transcribe(
        audio_path, task="transcribe", vad_filter=True, word_timestamps=word_timestamps
    )
    segments = list(segments)  # the generator is single-use; materialize once
    text = " ".join(seg.text.strip() for seg in segments).strip()

    words: list[dict] = []
    if word_timestamps:
        for seg in segments:
            for w in (seg.words or []):
                words.append({"word": w.word.strip(), "start": w.start, "end": w.end})

    return WhisperResult(
        text=text,
        language=info.language,
        language_probability=info.language_probability,
        duration=float(info.duration or 0.0),
        words=words,
    )
