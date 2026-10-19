"""Speech recognition for live sessions: the OpenAI-compatible transcription API
(OPENAI_BASE_URL, e.g. Groq whisper-large-v3). verbose_json gives word timestamps,
needed for pause and stutter timing. Without an API key there is no transcript and
word-level metrics are skipped. The local Whisper path was removed: docs/project/local-stt-removal.md
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.ai import get_openai_client, with_retries
from app.services.media import run_command

logger = logging.getLogger(__name__)

# OpenAI returns full language names in verbose_json
_LANGUAGE_CODES = {"english": "en", "malay": "ms", "indonesian": "id", "chinese": "zh", "tamil": "ta"}

# Whisper tends to "clean up" disfluencies. A prompt written with fillers
# nudges it to transcribe them verbatim, which the filler metric depends on;
# the Manglish in it nudges Whisper to keep code-switched words as spoken.
VERBATIM_PROMPT = "Umm, okay lah, so, uh, macam this week saya busy sikit, you know... but boleh la."


@dataclass
class ASRResult:
    transcript: str
    language: str
    confidence: float
    engine: str
    word_timestamps: list[dict] = field(default_factory=list)  # [{word, start, end}]


# ── Silence hallucinations ──────────────────────────────────────────────────
# Whisper writes stock phrases on silence or noise. Measured on Groq whisper-large-v3
# (docs/benchmarks/stt-groq-cloud-2026-10-15.md): 8 of 10 silent clips produced text, with
# no_speech_prob 0.24-0.72; 10 real-speech clips scored 0.001-0.097, including a genuine
# "Okay." inside speech. A segment is dropped when its no-speech probability is high, or
# moderately high and its text is a stock phrase or one or two words. Credits that only
# come from subtitle training data are dropped whatever the score.
NO_SPEECH_DROP = 0.4
NO_SPEECH_SUSPECT = 0.2
_CREDITS = re.compile(r"amara\.org|subtitles? by|thanks? (you )?for watching|please subscribe|like and subscribe", re.I)
_STOCK = {"you", "okay", "ok", "thank you", "thanks", "bye", "so", "uh", "um", "yeah", "hmm"}


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w' ]+", " ", text.lower()).split())


def is_hallucination(text: str, no_speech_prob: float | None = None) -> bool:
    """True when a transcribed segment is almost certainly not speech (see the note above)."""
    if _CREDITS.search(text):
        return True
    words = _norm(text) or ""
    if not words:
        return True
    if no_speech_prob is None:
        return False
    if no_speech_prob >= NO_SPEECH_DROP:
        return True
    return no_speech_prob >= NO_SPEECH_SUSPECT and (words in _STOCK or len(words.split()) <= 2)


def keep_speech(text: str, segments: list | None) -> tuple[str, list[tuple[float, float]]]:
    """The transcript without hallucinated segments, and the (start, end) spans that were kept.
    Without segments only the text itself can be checked."""
    if not segments:
        return ("", []) if is_hallucination(text) else (text.strip(), [])
    kept = [s for s in segments if not is_hallucination(_seg(s, "text") or "", _seg(s, "no_speech_prob"))]
    return " ".join((_seg(s, "text") or "").strip() for s in kept).strip(), [(_seg(s, "start"), _seg(s, "end")) for s in kept]


def _seg(segment, key):
    return segment.get(key) if isinstance(segment, dict) else getattr(segment, key, None)


async def to_flac(wav: Path) -> Path:
    """Lossless FLAC copy for upload: about a third of the WAV size (measured 2.1 vs 6.0 MB for
    3 min), so the 25 MB upload limit allows ~37 min of speech instead of ~13."""
    out = wav.with_suffix(".flac")
    await run_command([settings.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav), "-c:a", "flac", str(out)])
    return out


def stt_language() -> str | None:
    """Language to force on transcription (STT_LANGUAGE); None = auto-detect, which keeps Manglish as spoken."""
    return settings.stt_language if settings.stt_language not in ("", "auto") else None


async def _transcribe_openai(wav: Path, language: str | None = None) -> ASRResult | None:
    client = get_openai_client()
    if client is None:
        return None

    try:
        upload = await to_flac(wav)
    except Exception as e:  # noqa: BLE001 — fall back to the WAV (fine under ~13 min of speech)
        logger.warning("FLAC conversion failed, uploading WAV: %s", e)
        upload = wav

    async def verbose() -> ASRResult:
        with upload.open("rb") as f:
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model,
                file=f,
                prompt=VERBATIM_PROMPT,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"],
                **({"language": language} if language else {}),
            )
        detected = (getattr(resp, "language", None) or "english").lower()
        text, spans = keep_speech(resp.text, getattr(resp, "segments", None))
        words = [{"word": w.word.strip(), "start": w.start, "end": w.end} for w in (getattr(resp, "words", None) or [])]
        if getattr(resp, "segments", None):  # word timings of dropped segments go too
            words = [w for w in words if any(s - 0.05 <= w["start"] <= e + 0.05 for s, e in spans)]
        return ASRResult(
            transcript=text,
            language=_LANGUAGE_CODES.get(detected.split(" (")[0], detected[:2]),   # "malay (macrolanguage)" → ms
            confidence=1.0,
            engine=f"openai:{settings.transcription_model}",
            word_timestamps=words,
        )

    async def plain() -> ASRResult:
        with upload.open("rb") as f:
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model, file=f, prompt=VERBATIM_PROMPT
            )
        return ASRResult(
            transcript=keep_speech(resp.text, None)[0], language="en", confidence=1.0,
            engine=f"openai:{settings.transcription_model}",
        )

    try:
        return await with_retries(verbose, attempts=2, label="Whisper (verbose)")
    except Exception:  # noqa: BLE001 — some models (gpt-4o-transcribe) don't support verbose_json
        return await with_retries(plain, label="Whisper")


async def transcribe(wav_16k: Path, warnings: list[str], language: str | None = None) -> ASRResult | None:
    """Transcribe a 16 kHz mono WAV (auto language unless `language`). Appends to `warnings` for any fallback taken."""
    try:
        result = await _transcribe_openai(wav_16k, language)
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


async def transcribe_turn(audio: Path, context: str | None = None) -> str:
    """One spoken turn of a live conversation, as text (no word timings needed). `context` (what
    the turn answers) goes after the verbatim prompt, so Whisper spells topic words right. The
    server retries once; a failure raises so the router answers 502 and the browser retries too."""
    client = get_openai_client()
    lang = stt_language()
    # Whisper reads only the last ~224 prompt tokens: keep the verbatim style first, the context short
    prompt = f"{VERBATIM_PROMPT} {context.strip()[-400:]}" if context and context.strip() else VERBATIM_PROMPT

    async def call() -> str:
        with audio.open("rb") as f:
            # Segment no-speech probabilities let keep_speech drop text invented on a noise-only turn
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model, file=f, prompt=prompt,
                response_format="verbose_json", timestamp_granularities=["segment"],
                **({"language": lang} if lang else {}),
            )
        return keep_speech(resp.text, getattr(resp, "segments", None))[0]

    return await with_retries(call, attempts=2, base_delay=0.5, label="Whisper (turn)")
