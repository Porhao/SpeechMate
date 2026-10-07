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


def test_context_goes_in_the_prompt_and_its_echo_is_dropped(tmp_path, monkeypatch):
    """The question just asked helps Whisper with topic words; a segment that only repeats it
    (the AI's voice leaking into the mic) is not the user's answer."""
    from types import SimpleNamespace

    seen = {}

    class FakeModel:
        def transcribe(self, path, **kw):
            seen.update(kw)
            seg = lambda t: SimpleNamespace(text=t, no_speech_prob=0.1, avg_logprob=-0.2)  # noqa: E731
            return iter([seg("What tools did you use for the dashboard?"), seg("I used Power BI lah.")]), SimpleNamespace()

    monkeypatch.setattr(asr, "_whisper_model", lambda: FakeModel())
    segments, _ = asr.whisper_segments(tmp_path / "x.wav", None, context="Great. What tools did you use for the dashboard?")
    assert seen["initial_prompt"].startswith("Great. What tools did you use for the dashboard? ")
    assert [s.text for s in segments] == ["I used Power BI lah."]
