"""Speech-to-text for practice recordings (OpenAI Whisper)."""

import logging
from pathlib import Path

from app.config import settings
from app.services.ai import get_openai_client, with_retries

logger = logging.getLogger(__name__)

# Whisper tends to "clean up" disfluencies. A prompt written with fillers
# nudges it to transcribe them verbatim, which the filler metric depends on.
VERBATIM_PROMPT = "Umm, so, uh, I think, like, you know... Hmm, let me, erm, start again."


async def transcribe(audio_wav: Path) -> str | None:
    """Return a verbatim transcript, or None when no transcription backend is configured."""
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
