"""Speech recognition for live sessions: the OpenAI-compatible transcription API
(OPENAI_BASE_URL, e.g. Groq whisper-large-v3). verbose_json gives word timestamps,
needed for pause and stutter timing. Without an API key there is no transcript and
word-level metrics are skipped. The local Whisper path was removed: docs/project/local-stt-removal.md
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.ai import get_openai_client, with_retries
from app.services.coach.transcription import VERBATIM_PROMPT

logger = logging.getLogger(__name__)

# OpenAI returns full language names in verbose_json
_LANGUAGE_CODES = {"english": "en", "malay": "ms", "indonesian": "id", "chinese": "zh", "tamil": "ta"}


@dataclass
class ASRResult:
    transcript: str
    language: str
    confidence: float
    engine: str
    word_timestamps: list[dict] = field(default_factory=list)  # [{word, start, end}]


def stt_language() -> str | None:
    """Language to force on transcription (STT_LANGUAGE); None = auto-detect, which keeps Manglish as spoken."""
    return settings.stt_language if settings.stt_language not in ("", "auto") else None


async def _transcribe_openai(wav: Path) -> ASRResult | None:
    client = get_openai_client()
    if client is None:
        return None

    async def verbose() -> ASRResult:
        with wav.open("rb") as f:
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model,
                file=f,
                prompt=VERBATIM_PROMPT,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
        language = (getattr(resp, "language", None) or "english").lower()
        return ASRResult(
            transcript=resp.text.strip(),
            language=_LANGUAGE_CODES.get(language, language[:2]),
            confidence=1.0,
            engine=f"openai:{settings.transcription_model}",
            word_timestamps=[
                {"word": w.word.strip(), "start": w.start, "end": w.end}
                for w in (getattr(resp, "words", None) or [])
            ],
        )

    async def plain() -> ASRResult:
        with wav.open("rb") as f:
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model, file=f, prompt=VERBATIM_PROMPT
            )
        return ASRResult(
            transcript=resp.text.strip(), language="en", confidence=1.0,
            engine=f"openai:{settings.transcription_model}",
        )

    try:
        return await with_retries(verbose, attempts=2, label="Whisper (verbose)")
    except Exception:  # noqa: BLE001 — some models (gpt-4o-transcribe) don't support verbose_json
        return await with_retries(plain, label="Whisper")


async def transcribe(wav_16k: Path, warnings: list[str]) -> ASRResult | None:
    """Transcribe a 16 kHz mono WAV. Appends to `warnings` for any fallback taken."""
    try:
        result = await _transcribe_openai(wav_16k)
    except Exception as e:  # noqa: BLE001
        warnings.append(f"Transcription failed ({e}); word-level metrics were skipped.")
        return None
    if result is None:
        warnings.append(
            "No speech recognition available (set OPENAI_API_KEY): "
            "pace, fillers, stuttering repetitions, pronunciation and language metrics were skipped."
        )
    elif not result.word_timestamps:
        warnings.append("The transcription model returned no word timings; pauses were measured from the audio instead.")
    return result
