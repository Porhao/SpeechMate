"""
ASR Service — Automatic Speech Recognition.

Routes each real transcription between two engines instead of running
everything through one general-purpose model (see whisper_engine.py /
codeswitch_engine.py for why):

  1. faster-whisper always runs first, with word timestamps — those are
     needed downstream for pause/articulation-rate analysis (fluency.py)
     and stuttering timing, and only Whisper produces them.
  2. If Whisper is confident the clip is English, its transcript is kept.
  3. Otherwise (Malay, or Whisper isn't confident — which in practice
     correlates with code-switched speech confusing it) the same audio is
     re-run through Mesolitica's code-switching model
     (mesolitica/wav2vec2-xls-r-300m-mixed) and THAT transcript replaces the
     text. Whisper's word timestamps are still used for timing — they're
     audio-driven, not text-driven, so they stay a reasonable approximation
     even when the transcribed words themselves changed.
"""
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from app.ai.speech import whisper_engine, codeswitch_engine
from app.ai.speech.pipeline import ENGLISH_CONFIDENCE_THRESHOLD, load_16k_mono

logger = logging.getLogger(__name__)


@dataclass
class ASRResult:
    transcript: str
    language: str
    confidence: float
    word_timestamps: list[dict]
    duration_seconds: float
    engine_used: str = "faster-whisper"


class ASRService:
    """
    Wraps the whisper/code-switching routing pipeline for speech-to-text.

    Models load lazily on first real transcription request (keeps app
    startup fast) and are cached process-wide by whisper_engine /
    codeswitch_engine — this class holds no model state of its own.
    Falls back to a stub result if no audio file is available, or if
    inference fails for any reason (missing file, corrupt upload, a
    code-switching model that failed to download, etc.) so the rest of the
    pipeline never hard-crashes on ASR.
    """

    def __init__(self, use_real_model: bool = True):
        self.use_real_model = use_real_model

    async def transcribe(self, audio_path: str | Path) -> ASRResult:
        if self.use_real_model and audio_path and Path(audio_path).is_file():
            try:
                return await asyncio.to_thread(self._transcribe_real, audio_path)
            except Exception:
                logger.exception("Real ASR failed for %s — falling back to stub", audio_path)
        return self._transcribe_stub(audio_path)

    def _transcribe_real(self, audio_path: str | Path) -> ASRResult:
        whisper_result = whisper_engine.transcribe(str(audio_path), word_timestamps=True)
        transcript = whisper_result.text
        engine_used = "faster-whisper"

        confident_english = (
            whisper_result.language == "en"
            and whisper_result.language_probability >= ENGLISH_CONFIDENCE_THRESHOLD
        )
        if not confident_english:
            try:
                audio, sr = load_16k_mono(str(audio_path))
                cs_result = codeswitch_engine.transcribe(audio, sr)
                if cs_result.text:
                    transcript = cs_result.text
                    engine_used = cs_result.engine
            except Exception:
                # Code-switching model unavailable (e.g. weights not
                # downloaded yet) — Whisper's own transcript is still a
                # valid answer, just without the code-switching accuracy
                # boost, so don't fail the whole request over it.
                logger.exception(
                    "Code-switching ASR failed for %s — keeping Whisper transcript", audio_path
                )

        return ASRResult(
            transcript=transcript,
            language=whisper_result.language or "en",
            confidence=round(float(whisper_result.language_probability or 0.0), 3),
            word_timestamps=whisper_result.words,
            duration_seconds=whisper_result.duration,
            engine_used=engine_used,
        )

    def _transcribe_stub(self, _audio_path: str | Path) -> ASRResult:
        return ASRResult(
            transcript=(
                "Good morning everyone. Today I would like to present my research project "
                "on AI-powered speech analysis. Um, this system can detect stuttering and "
                "evaluate pronunciation in real time."
            ),
            language="en",
            confidence=0.97,
            word_timestamps=[
                {"word": "Good", "start": 0.0, "end": 0.3},
                {"word": "morning", "start": 0.3, "end": 0.7},
                {"word": "everyone", "start": 0.7, "end": 1.2},
            ],
            duration_seconds=18.5,
            engine_used="stub",
        )


# Singleton — import and use directly
asr_service = ASRService()
