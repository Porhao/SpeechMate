"""
Speech transcription pipeline — routes each session recording to whichever
engine is actually good at it, instead of running everything through one
general-purpose model.

    1. faster-whisper always runs first. It's cheap relative to the
       code-switching model, and its own language guess is the routing
       signal — no separate language-ID model or dependency needed.
    2. If Whisper is confident the clip is English, its transcript is the
       answer. Whisper genuinely is a strong English ASR engine; there's no
       reason to also pay for the heavier pass.
    3. Otherwise (Malay, or Whisper isn't confident — which in practice
       correlates with code-switched speech confusing it) the same audio is
       re-run through the Mesolitica code-switching model, and THAT
       transcript is what ships. Whisper's transcript is kept alongside it
       as the "raw Whisper baseline" the methodology page's WER comparison
       needs — this pipeline produces both sides of that comparison for
       free, it just doesn't compute WER itself (that needs a reference
       transcript, which only exists for a held-out eval set, not live
       sessions).
    4. english_ratio / malay_ratio / is_code_switching are derived from
       whichever transcript actually shipped, via the lexicon heuristic —
       see lexicon.py for exactly what that does and doesn't get right.

Everything is pretrained inference — no fine-tuning, no training loop. If
accuracy on Malaysian-accented audio still isn't where the FYP evaluation
needs it, the next lever is a held-out labelled test set and this
threshold/routing logic, not retraining either model.
"""

from __future__ import annotations
from dataclasses import dataclass, field

import librosa

from app.ai.speech import whisper_engine, codeswitch_engine, lexicon

# Below this confidence, Whisper's own language guess isn't trusted enough
# to skip the code-switching model — err toward the model built for mixed
# speech rather than a shaky "it's English" call.
ENGLISH_CONFIDENCE_THRESHOLD = 0.80


@dataclass
class LanguageAnalysis:
    primary_language: str
    is_code_switching: bool
    accent_type: str
    english_ratio: float
    malay_ratio: float


@dataclass
class TranscriptionResult:
    transcript: str
    engine_used: str                 # "faster-whisper" | codeswitch_engine.MODEL_ID
    language: LanguageAnalysis
    whisper_baseline: str = field(default="")   # always populated when the code-switch path ran
    whisper_language_probability: float = 0.0


def load_16k_mono(audio_path: str):
    # librosa resamples on load; sr=16000 forces the target rate the
    # code-switching model requires regardless of the source file's rate.
    # Public — also used directly by speech/asr.py, which needs the
    # code-switching engine's audio prep but not this whole function's
    # routing decision (it makes its own, since it also needs Whisper's
    # word timestamps that transcribe_session() below doesn't request).
    audio, sr = librosa.load(audio_path, sr=codeswitch_engine.SAMPLE_RATE, mono=True)
    return audio, sr


def transcribe_session(audio_path: str) -> TranscriptionResult:
    whisper_result = whisper_engine.transcribe(audio_path)

    used_codeswitch = not (
        whisper_result.language == "en"
        and whisper_result.language_probability >= ENGLISH_CONFIDENCE_THRESHOLD
    )

    if used_codeswitch:
        audio, sr = load_16k_mono(audio_path)
        cs_result = codeswitch_engine.transcribe(audio, sr)
        final_text = cs_result.text or whisper_result.text  # fall back if CTC decode came back empty
        engine_used = cs_result.engine
    else:
        final_text = whisper_result.text
        engine_used = "faster-whisper"

    english_ratio, malay_ratio = lexicon.estimate_language_ratio(final_text)
    code_switching = lexicon.is_code_switching(english_ratio, malay_ratio)

    primary_language = "ms" if malay_ratio > english_ratio else "en"
    accent_type = "Malaysian English" if primary_language == "en" else "Bahasa Malaysia (Malaysian)"

    return TranscriptionResult(
        transcript=final_text,
        engine_used=engine_used,
        whisper_baseline=whisper_result.text if used_codeswitch else "",
        whisper_language_probability=whisper_result.language_probability,
        language=LanguageAnalysis(
            primary_language=primary_language,
            is_code_switching=code_switching,
            accent_type=accent_type,
            english_ratio=english_ratio,
            malay_ratio=malay_ratio,
        ),
    )
