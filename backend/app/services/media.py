"""Audio helpers built on the ffmpeg CLI: running commands, WAV durations, silences, peak level."""

import asyncio
import logging
import re
import wave
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

class MediaError(Exception):
    """Raised when an ffmpeg (or other media) command fails."""


async def run_command(cmd: list[str], timeout: float = 300) -> tuple[str, str]:
    """Run a subprocess, returning (stdout, stderr). Raises MediaError on failure."""
    logger.debug("Running: %s", " ".join(cmd))
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as e:  # not installed, or not executable
        raise MediaError(f"Could not run {cmd[0]}: {e.strerror or e}") from e

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError as e:
        process.kill()
        await process.wait()
        raise MediaError(f"{Path(cmd[0]).name} timed out after {timeout:.0f}s") from e

    out = stdout.decode(errors="replace")
    err = stderr.decode(errors="replace")
    if process.returncode != 0:
        tail = "\n".join(err.strip().splitlines()[-5:])
        raise MediaError(f"{Path(cmd[0]).name} failed (exit {process.returncode}): {tail}")
    return out, err


def wav_duration(path: Path) -> float:
    """Duration in seconds of a PCM WAV file."""
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


_SILENCE_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([\d.]+)")


_MAX_VOLUME = re.compile(r"max_volume:\s*(-?[\d.]+) dB")
LOUD_PEAK_DB = -3.0   # a normal recording (browser auto-gain) peaks around here
QUIET_FLOOR_DB, MIN_NOISE_DB = -60.0, -80.0


async def peak_db(path: Path) -> float | None:
    """The recording's peak level in dBFS (ffmpeg volumedetect), or None if unreadable."""
    _, err = await run_command([settings.ffmpeg_bin, "-hide_banner", "-nostats", "-i", str(path),
                                "-af", "volumedetect", "-f", "null", "-"])
    m = _MAX_VOLUME.search(err)
    return float(m.group(1)) if m else None


async def detect_silences(
    path: Path, noise_db: float = -35.0, min_duration: float = 0.7
) -> list[tuple[float, float]]:
    """Return (start, end) pairs of silent stretches, via ffmpeg's silencedetect filter.

    The threshold is relative to the recording's own peak: `noise_db` applies to a recording
    peaking at LOUD_PEAK_DB or louder, and a quieter one gets a threshold lowered by the same
    amount. Otherwise a quiet microphone (peak −44 dB, say) reads as all silence and the speech
    is rejected as missing."""
    peak = await peak_db(path)
    # Only for a usable signal (≥ -60 dB peak; quieter is digital silence or hiss), and never below
    # -80 dB, where ffmpeg's detector stops finding silence even in pure zeros
    if peak is not None and QUIET_FLOOR_DB <= peak < LOUD_PEAK_DB:
        noise_db = max(noise_db + peak - LOUD_PEAK_DB, MIN_NOISE_DB)
    _, err = await run_command([
        settings.ffmpeg_bin, "-hide_banner", "-nostats",
        "-i", str(path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-",
    ])
    silences: list[tuple[float, float]] = []
    start: float | None = None
    for line in err.splitlines():
        if m := _SILENCE_START.search(line):
            start = max(float(m.group(1)), 0.0)
        elif (m := _SILENCE_END.search(line)) and start is not None:
            silences.append((start, float(m.group(1))))
            start = None
    if start is not None:  # silence ran to the end of the file
        try:
            silences.append((start, wav_duration(path)))
        except (wave.Error, EOFError):
            pass
    return silences
