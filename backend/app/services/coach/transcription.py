"""Speech-to-text for presentation practice recordings: the OpenAI-compatible Whisper API."""

import logging
from pathlib import Path

from app.config import settings
from app.services.ai import get_openai_client, with_retries

logger = logging.getLogger(__name__)

# Whisper tends to "clean up" disfluencies. A prompt written with fillers
# nudges it to transcribe them verbatim, which the filler metric depends on;
# the Manglish in it nudges Whisper to keep code-switched words as spoken.
VERBATIM_PROMPT = "Umm, okay lah, so, uh, macam this week saya busy sikit, you know... but boleh la."


async def transcribe(audio_wav: Path) -> str | None:
    """Return a verbatim transcript, or None when no transcription backend is available."""
    client = get_openai_client()
    if client is None:
        return None

    from app.services.live.asr import stt_language  # lazy: live.asr imports this module

    lang = stt_language()

    async def call() -> str:
        with audio_wav.open("rb") as f:
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model,
                file=f,
                prompt=VERBATIM_PROMPT,
                **({"language": lang} if lang else {}),
            )
        return resp.text.strip()

    return await with_retries(call, label="Whisper transcription")
