"""
Shared audio decoding helper.

Uses PyAV (bundles its own libav — no system ffmpeg binary required) to pull
the audio track out of any container the browser hands us (webm/opus, mp4,
wav, ...) and resample it to mono float32 @ 16kHz, the format every speech
model in this pipeline expects.
"""
from pathlib import Path

import numpy as np

TARGET_SR = 16000


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """
    Decode the audio track of `path` into a mono float32 waveform at 16kHz.
    Returns (waveform, sample_rate). Raises on decode failure — callers
    should catch and fall back to stub behaviour.
    """
    import av

    container = av.open(str(path))
    stream = next((s for s in container.streams if s.type == "audio"), None)
    if stream is None:
        raise ValueError(f"No audio stream found in {path}")

    resampler = av.AudioResampler(format="s16", layout="mono", rate=TARGET_SR)

    chunks: list[np.ndarray] = []
    for frame in container.decode(stream):
        for resampled in resampler.resample(frame):
            arr = resampled.to_ndarray()
            chunks.append(arr.reshape(-1))

    container.close()

    if not chunks:
        return np.zeros(0, dtype=np.float32), TARGET_SR

    pcm = np.concatenate(chunks).astype(np.float32) / 32768.0
    return pcm, TARGET_SR
