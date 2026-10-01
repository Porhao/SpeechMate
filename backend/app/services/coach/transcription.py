"""Speech-to-text for presentation practice recordings: local faster-whisper when
installed (requirements-ml.txt), otherwise the OpenAI Whisper API."""

import asyncio
import logging
from pathlib import Path

from app.config import settings
from app.services.ai import get_openai_client, with_retries

logger = logging.getLogger(__name__)

# Whisper tends to "clean up" disfluencies. A prompt written with fillers
# nudges it to transcribe them verbatim, which the filler metric depends on;
# the Manglish in it nudges Whisper to keep code-switched words as spoken.
VERBATIM_PROMPT = "Umm, okay lah, so, uh, macam this week saya busy sikit, you know... but boleh la."


def _transcribe_local(audio_wav: Path) -> str:
    from app.services.live.asr import whisper_language, whisper_segments  # lazy: live.asr imports this module

    segments, _ = whisper_segments(audio_wav, whisper_language())
    return " ".join(seg.text.strip() for seg in segments).strip()


async def transcribe(audio_wav: Path) -> str | None:
    """Return a verbatim transcript, or None when no transcription backend is available."""
    from app.services.live._ml import available

    if available("faster_whisper"):
        try:
            return await asyncio.to_thread(_transcribe_local, audio_wav)
        except Exception as e:  # noqa: BLE001 — try the API instead
            logger.error("Local transcription failed, trying the OpenAI API: %s", e)

    client = get_openai_client()
    if client is None:
        return None

    async def call() -> str:
        with audio_wav.open("rb") as f:
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model,
                file=f,
                language="en",
                prompt=VERBATIM_PROMPT,
            )
        return resp.text.strip()

    return await with_retries(call, label="Whisper transcription")
