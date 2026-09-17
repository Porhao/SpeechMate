"""
Speech analysis — ASR routed between faster-whisper (English) and
Mesolitica's code-switching wav2vec2 model (Malay / mixed), plus a
lexicon-based English/Malay ratio estimate. See pipeline.py for the routing
logic and lexicon.py for exactly what the ratio estimate does and doesn't
get right.

    from app.ai.speech import transcribe_session
    result = transcribe_session("/path/to/recording.wav")
"""

from app.ai.speech.pipeline import transcribe_session, TranscriptionResult, LanguageAnalysis

__all__ = ["transcribe_session", "TranscriptionResult", "LanguageAnalysis"]
