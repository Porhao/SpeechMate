"""Silence must give an empty transcript, not a crash (faster-whisper + VAD + auto-detect)."""
import wave

import pytest

from app.services.live import asr
from app.services.live._ml import available


@pytest.mark.skipif(not available("faster_whisper"), reason="needs requirements-ml.txt")
def test_silence_gives_empty_transcript(tmp_path):
    path = tmp_path / "silence.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0\0" * 16000 * 3)
    segments, info = asr.whisper_segments(path, None)
    assert segments == [] and info is None
    assert asr._transcribe_local(path, []).transcript == ""
