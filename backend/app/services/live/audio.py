"""Audio preparation for the live-session models: every model here expects
16 kHz mono PCM, produced once with ffmpeg."""

import wave
from pathlib import Path

from app.config import settings
from app.services.media import run_command

MODEL_SAMPLE_RATE = 16000


async def to_16k_wav(src: Path, dst: Path) -> Path:
    """Extract the audio track of any recording (webm/mp4/wav…) as 16 kHz mono WAV."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    await run_command([
        settings.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src), "-vn", "-ac", "1", "-ar", str(MODEL_SAMPLE_RATE), "-c:a", "pcm_s16le",
        str(dst),
    ])
    return dst


def load_wav_float(path: Path):
    """16-bit PCM WAV → mono float32 numpy array in [-1, 1] (needs numpy, from requirements-ml.txt)."""
    import numpy as np

    with wave.open(str(path), "rb") as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0
