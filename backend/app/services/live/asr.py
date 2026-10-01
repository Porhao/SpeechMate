"""Speech recognition for live sessions, routed per clip.

1. Local faster-whisper (requirements-ml.txt) runs first, with word
   timestamps (needed for pause and stutter timing) and its own language
   guess as the routing signal.
2. If Whisper isn't confident the clip is English — Malay, or code-switched
   speech confusing it — the audio is re-run through Mesolitica's
   code-switching model (mesolitica/wav2vec2-xls-r-300m-mixed, trained on
   Malay + Singlish + Mandarin-mixed speech) and THAT transcript is kept.
   Whisper's word timestamps are still used: they're audio-driven, so they
   stay a reasonable approximation even when the words changed.
3. Without local models, the OpenAI transcription API is used instead
   (verbose_json gives word timestamps with whisper-1).
4. With neither, there is no transcript and word-level metrics are skipped.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.ai import get_openai_client, with_retries
from app.services.coach.transcription import VERBATIM_PROMPT
from app.services.live._ml import available, load_once

logger = logging.getLogger(__name__)

# Below this, Whisper's "it's English" guess isn't trusted enough to skip the
# code-switching model.
ENGLISH_CONFIDENCE_THRESHOLD = 0.80
CODESWITCH_MODEL_ID = "mesolitica/wav2vec2-xls-r-300m-mixed"

# OpenAI returns full language names in verbose_json
_LANGUAGE_CODES = {"english": "en", "malay": "ms", "indonesian": "id", "chinese": "zh", "tamil": "ta"}


@dataclass
class ASRResult:
    transcript: str
    language: str
    confidence: float
    engine: str
    word_timestamps: list[dict] = field(default_factory=list)  # [{word, start, end}]


def is_malaysian_model() -> bool:
    """Mesolitica's Malaysian Whisper already handles Malay/English/Manglish itself."""
    return "malaysian-whisper" in settings.whisper_model_size.lower()


def whisper_language(default_for_standard: str | None = "en") -> str | None:
    """The language token to transcribe with (see settings.stt_language); None = auto-detect."""
    if settings.stt_language == "auto":
        return None
    if settings.stt_language:
        return settings.stt_language
    # Malaysian Whisper auto-detects reliably and then transcribes in the language spoken.
    # Forcing "ms" makes it *translate* English speech into Malay when there's no English
    # prompt (seen on US/UK-accented answers); auto-detect was also better on real Malay
    # (6.4% vs 7.4% WER, docs/benchmarks/stt-benchmark-2026-10-01.md).
    return None if is_malaysian_model() else default_for_standard


@load_once
def _whisper_model():
    from faster_whisper import WhisperModel

    logger.info("Loading faster-whisper '%s' (CPU, int8)…", settings.whisper_model_size)
    return WhisperModel(
        settings.whisper_model_size, device="cpu", compute_type="int8", cpu_threads=settings.whisper_cpu_threads
    )


@load_once
def _codeswitch_model():
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    logger.info("Loading code-switching ASR '%s'…", CODESWITCH_MODEL_ID)
    model = Wav2Vec2ForCTC.from_pretrained(CODESWITCH_MODEL_ID)
    model.eval()
    return Wav2Vec2Processor.from_pretrained(CODESWITCH_MODEL_ID), model


def _codeswitch_transcribe(wav_16k: Path) -> str:
    import torch

    from app.services.live.audio import load_wav_float

    audio = load_wav_float(wav_16k)
    processor, model = _codeswitch_model()
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(inputs.input_values).logits
    return processor.batch_decode(torch.argmax(logits, dim=-1))[0].strip()


def _transcribe_local(wav_16k: Path, warnings: list[str]) -> ASRResult:
    malaysian = is_malaysian_model()
    segments, info = _whisper_model().transcribe(
        str(wav_16k), task="transcribe", vad_filter=True, word_timestamps=True,
        # Auto-detect for both: the detected language is the routing signal below
        language=whisper_language(default_for_standard=None),
    )
    segments = list(segments)  # single-use generator
    words = [
        {"word": w.word.strip(), "start": w.start, "end": w.end}
        for seg in segments for w in (seg.words or [])
    ]
    result = ASRResult(
        transcript=" ".join(seg.text.strip() for seg in segments).strip(),
        language=info.language or "en",
        confidence=round(float(info.language_probability or 0.0), 3),
        engine=f"faster-whisper ({Path(settings.whisper_model_size).name})",
        word_timestamps=words,
    )
    if malaysian:
        return result  # already Malaysian-tuned: no need to re-run the code-switching model

    confident_english = result.language == "en" and result.confidence >= ENGLISH_CONFIDENCE_THRESHOLD
    if not confident_english:
        if available("transformers", "torch", "numpy"):
            try:
                text = _codeswitch_transcribe(wav_16k)
                if text:
                    result.transcript, result.engine = text, CODESWITCH_MODEL_ID
            except Exception as e:  # noqa: BLE001 — Whisper's transcript is still valid
                logger.exception("Code-switching ASR failed")
                warnings.append(f"Code-switching ASR failed ({e}); kept the Whisper transcript.")
        else:
            warnings.append(
                "Speech looked non-English or code-switched, but the code-switching model isn't "
                "installed (requirements-ml.txt); kept the Whisper transcript."
            )
    return result


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
    if available("faster_whisper"):
        try:
            return await asyncio.to_thread(_transcribe_local, wav_16k, warnings)
        except Exception as e:  # noqa: BLE001
            logger.exception("Local ASR failed")
            warnings.append(f"Local speech recognition failed ({e}); trying the OpenAI API.")

    try:
        result = await _transcribe_openai(wav_16k)
    except Exception as e:  # noqa: BLE001
        warnings.append(f"Transcription failed ({e}); word-level metrics were skipped.")
        return None
    if result is None:
        warnings.append(
            "No speech recognition available (install requirements-ml.txt or set OPENAI_API_KEY): "
            "pace, fillers, stuttering repetitions, pronunciation and language metrics were skipped."
        )
    elif not result.word_timestamps:
        warnings.append("The transcription model returned no word timings; pauses were measured from the audio instead.")
    return result
