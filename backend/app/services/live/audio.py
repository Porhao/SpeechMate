"""The recording's audio for the live analysis: 16 kHz mono PCM (what every model here expects,
produced once with ffmpeg), its duration, silences and peak level, and a FLAC copy for upload."""

import re
import wave
from pathlib import Path

from app.services.media import ffmpeg

MODEL_SAMPLE_RATE = 16000


async def to_16k_wav(src: Path, dst: Path) -> Path:
    """Extract the audio track of any recording (webm/mp4/wav…) as 16 kHz mono WAV."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    await ffmpeg("-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(MODEL_SAMPLE_RATE),
                 "-c:a", "pcm_s16le", str(dst))
    return dst


def load_wav_float(path: Path):
    """16-bit PCM WAV → mono float32 numpy array in [-1, 1] (needs numpy, from requirements-ml.txt)."""
    import numpy as np

    with wave.open(str(path), "rb") as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0


async def to_flac(wav: Path) -> Path:
    """Lossless FLAC copy for upload: about a third of the WAV size (measured 2.1 vs 6.0 MB for
    3 min), so the 25 MB upload limit allows ~37 min of speech instead of ~13."""
    out = wav.with_suffix(".flac")
    await ffmpeg("-y", "-loglevel", "error", "-i", str(wav), "-c:a", "flac", str(out))
    return out


def wav_duration(path: Path) -> float:
    """Duration in seconds of a PCM WAV file."""
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


_SILENCE_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([\d.]+)")


_MAX_VOLUME = re.compile(r"max_volume:\s*(-?[\d.]+) dB")
LOUD_PEAK_DB = -3.0   # a normal recording (browser auto-gain) peaks around here
QUIET_FLOOR_DB, MIN_NOISE_DB = -60.0, -80.0
NOISE_DB = -35.0      # silence threshold for a normally loud recording


async def peak_db(path: Path) -> float | None:
    """The recording's peak level in dBFS (ffmpeg volumedetect), or None if unreadable."""
    _, err = await ffmpeg("-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-")
    m = _MAX_VOLUME.search(err)
    return float(m.group(1)) if m else None


async def detect_silences(path: Path, min_duration: float) -> list[tuple[float, float]]:
    """Return (start, end) pairs of silent stretches, via ffmpeg's silencedetect filter.

    The threshold is relative to the recording's own peak: NOISE_DB applies to a recording
    peaking at LOUD_PEAK_DB or louder, and a quieter one gets a threshold lowered by the same
    amount. Otherwise a quiet microphone (peak −44 dB, say) reads as all silence and the speech
    is rejected as missing."""
    noise_db = NOISE_DB
    peak = await peak_db(path)
    # Only for a usable signal (≥ -60 dB peak; quieter is digital silence or hiss), and never below
    # -80 dB, where ffmpeg's detector stops finding silence even in pure zeros
    if peak is not None and QUIET_FLOOR_DB <= peak < LOUD_PEAK_DB:
        noise_db = max(noise_db + peak - LOUD_PEAK_DB, MIN_NOISE_DB)
    _, err = await ffmpeg("-nostats", "-i", str(path), "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}", "-f", "null", "-")
    silences: list[tuple[float, float]] = []
    start: float | None = None
    for line in err.splitlines():
        if m := _SILENCE_START.search(line):
            start = max(float(m.group(1)), 0.0)
        elif (m := _SILENCE_END.search(line)) and start is not None:
            silences.append((start, float(m.group(1))))
            start = None
    if start is not None:  # silence ran to the end of the file
        silences.append((start, wav_duration(path)))
    return silences
