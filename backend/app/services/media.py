"""Running media command-line tools (ffmpeg, LibreOffice, pdftoppm) with a timeout."""

import asyncio
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class MediaError(Exception):
    """A media command failed (its message is technical: for the log, not the user)."""


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


async def ffmpeg(*args: str, timeout: float = 300) -> tuple[str, str]:
    """Run ffmpeg quietly with these arguments; (stdout, stderr). Raises MediaError on failure."""
    return await run_command([settings.ffmpeg_bin, "-hide_banner", *args], timeout=timeout)
