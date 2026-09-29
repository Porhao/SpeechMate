"""Audio/video helpers built on the ffmpeg CLI.

Every audio artifact in the system is normalized to one WAV format
(44.1 kHz, mono, 16-bit PCM) so durations can be read with the stdlib
`wave` module and ffprobe is never needed.
"""

import asyncio
import logging
import re
import wave
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
# Short silence appended after each slide so transitions don't feel rushed
SLIDE_GAP_SEC = 0.5


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


async def normalize_to_wav(src: Path, dst: Path) -> Path:
    """Convert any audio (or video with an audio track) to the canonical WAV format."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    await run_command([
        settings.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le",
        str(dst),
    ])
    return dst


def wav_duration(path: Path) -> float:
    """Duration in seconds of a PCM WAV file."""
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def write_silence_wav(path: Path, duration_sec: float) -> Path:
    """Write a silent WAV of the given duration (pure Python, no ffmpeg needed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(SAMPLE_RATE * max(duration_sec, 0.5))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(b"\x00\x00" * frames)
    return path


_SILENCE_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([\d.]+)")


async def detect_silences(
    path: Path, noise_db: float = -35.0, min_duration: float = 0.7
) -> list[tuple[float, float]]:
    """Return (start, end) pairs of silent stretches, via ffmpeg's silencedetect filter."""
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


async def render_slide_segment(png: Path, wav: Path, out: Path, duration_sec: float) -> Path:
    """Render one slide image + its narration into an MP4 segment."""
    out.parent.mkdir(parents=True, exist_ok=True)
    total = duration_sec + SLIDE_GAP_SEC
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p"
    )
    await run_command([
        settings.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", "10", "-i", str(png),
        "-i", str(wav),
        "-t", f"{total:.3f}",
        "-vf", vf,
        "-af", f"apad=pad_dur={SLIDE_GAP_SEC}",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-r", "10",
        "-c:a", "aac", "-b:a", "128k", "-ar", str(SAMPLE_RATE), "-ac", "1",
        str(out),
    ])
    return out


async def concat_segments(segments: list[Path], out: Path) -> Path:
    """Concatenate identically-encoded MP4 segments into one video (no re-encode)."""
    list_file = out.parent / "segments.txt"
    list_file.write_text(
        "".join(f"file '{seg.resolve().as_posix()}'\n" for seg in segments)
    )
    await run_command([
        settings.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", "-movflags", "+faststart",
        str(out),
    ])
    return out
