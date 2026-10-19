"""Step-1 fixes: silence hallucinations dropped, FLAC upload, server-side Gaze Tunneling, session usage."""

import random
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.live import asr, extra_metrics
from app.services.live.pipeline import session_usage

# (text, no_speech_prob) as Groq whisper-large-v3 returned them (docs/benchmarks/stt-groq-cloud-2026-10-15.md)
SILENT = [("Subtitles by the Amara.org community", 0.384), ("Okay.", 0.363), (".", 0.389),
          ("Subtitles by the Amara.org community", 0.244), ("Okay.", 0.514), ("So, I'm going to go to the next place.", 0.493),
          ("you", 0.722)]
SPEECH = [("Many people don't think about them as dinosaurs.", 0.055), ("A civilization is a singular culture.", 0.097),
          ("Okay.", 0.001), ("Memang aku bagi tips lebih.", 0.001)]


def test_silence_hallucinations_dropped_real_speech_kept():
    assert all(asr.is_hallucination(t, p) for t, p in SILENT)
    assert not any(asr.is_hallucination(t, p) for t, p in SPEECH)  # incl. a genuine "Okay." inside speech
    # Without segment scores only the subtitle credits are certain
    assert asr.is_hallucination("Thanks for watching!") and not asr.is_hallucination("Okay.")


def test_keep_speech_drops_only_the_hallucinated_segment():
    segs = [{"text": " I built the dashboard.", "no_speech_prob": 0.02, "start": 0.0, "end": 2.0},
            {"text": " Subtitles by the Amara.org community", "no_speech_prob": 0.3, "start": 2.0, "end": 6.0}]
    text, spans = asr.keep_speech("I built the dashboard. Subtitles by the Amara.org community", segs)
    assert text == "I built the dashboard." and spans == [(0.0, 2.0)]
    assert asr.keep_speech("you", [{"text": "you", "no_speech_prob": 0.72, "start": 0, "end": 8}]) == ("", [])


async def test_analysis_drops_word_timings_of_dropped_segments(monkeypatch, tmp_path):
    resp = SimpleNamespace(
        text="Um, I led the team. Okay.", language="english",
        words=[SimpleNamespace(word=w, start=s, end=s + 0.3) for w, s in [("Um,", 0.1), ("I", 0.5), ("led", 0.8), ("the", 1.1), ("team.", 1.4), ("Okay.", 9.0)]],
        segments=[{"text": " Um, I led the team.", "no_speech_prob": 0.01, "start": 0.0, "end": 1.8},
                  {"text": " Okay.", "no_speech_prob": 0.5, "start": 8.5, "end": 9.5}],
    )

    async def create(**_):
        return resp
    monkeypatch.setattr(asr, "get_openai_client", lambda: SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))))

    async def same(wav):
        return wav
    monkeypatch.setattr(asr, "to_flac", same)
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    r = await asr._transcribe_openai(wav)
    assert r.transcript == "Um, I led the team."
    assert [w["word"] for w in r.word_timestamps] == ["Um,", "I", "led", "the", "team."]


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_flac_upload_is_smaller_and_lossless(tmp_path):
    from tests.test_e2e import _tone_wav

    wav = tmp_path / "turn.wav"
    wav.write_bytes(_tone_wav([(3, True), (2, False), (3, True)]))
    flac = await asr.to_flac(wav)
    assert flac.suffix == ".flac" and flac.stat().st_size < wav.stat().st_size
    pcm = lambda p: subprocess.run([settings.ffmpeg_bin, "-v", "error", "-i", str(p), "-f", "s16le", "-"],
                                   capture_output=True, check=True).stdout
    assert pcm(flac) == pcm(wav)


def test_disfluency_times_from_word_timings_and_stutter_events():
    words = [{"word": "Um,", "start": 1.0}, {"word": "I", "start": 1.4}, {"word": "uh", "start": 7.2}]
    events = [{"type": "Block", "start_time": 12.0}, {"type": "Prolongation", "start_time": None}]
    assert extra_metrics.disfluency_times(words, events) == [1.0, 7.2, 12.0]
    assert [(e["type"], e["t_sec"]) for e in extra_metrics.disfluency_events(words, events)] == [
        ("filler", 1.0), ("filler", 7.2), ("block", 12.0)]


def test_gaze_tunneling_finds_a_real_link_and_ignores_chance():
    duration = 150.0  # 30 windows of 5 s
    stumbles = [3, 10, 17, 24]  # windows where the speaker looks away AND hesitates twice
    gaze = [(w * 5 + k, w in stumbles) for w in range(30) for k in (0.5, 2.5, 4.5)]
    events = [w * 5 + 1.0 for w in stumbles for _ in range(2)]
    gt = extra_metrics.gaze_tunneling(gaze, events, duration)
    assert gt["r"] == 1.0 and gt["p"] == round(1 / 30, 3) and gt["label"] == "Strong link"

    rng = random.Random(1)  # stumbles unrelated to where they look
    gaze = [(t, rng.random() < 0.3) for t in [i * 0.5 for i in range(300)]]
    events = sorted(rng.uniform(0, duration) for _ in range(12))
    assert extra_metrics.gaze_tunneling(gaze, events, duration)["label"] == "No clear link"

    assert extra_metrics.gaze_tunneling(gaze, events, 60.0) is None   # 12 windows: p can't reach 0.05
    assert extra_metrics.gaze_tunneling(gaze, events[:2], duration) is None


def test_session_usage_bills_each_turn_at_least_10_seconds():
    u = session_usage({"calls": 3, "prompt_tokens": 900, "completion_tokens": 120},
                      {"calls": 2, "prompt_tokens": 2000, "completion_tokens": 400},
                      {"stt_audio_sec": [4.0, 12.0, 0, "x"]}, 150.0)
    assert u["stt"]["turn_requests"] == 2 and u["stt"]["billed_sec"] == 10 + 12 + 150
    assert u["stt"]["usd"] == round(172 / 3600 * 0.111, 5)
    assert u["llm"]["calls"] == 5 and u["llm"]["prompt_tokens"] == 2900 and u["llm"]["completion_tokens"] == 520
    assert u["llm"]["usd"] == round((2900 * 0.30 + 520 * 2.50) / 1e6, 5)   # Gemini 3.5 Flash-Lite list price


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_quiet_recording_is_not_read_as_silence(tmp_path):
    """A clip peaking at -44 dB (a quiet microphone; FLEURS en_004) was rejected as 'no speech'
    by the fixed -35 dB threshold. The threshold now follows the recording's own peak."""
    import math
    import struct
    import wave

    from app.services.media import detect_silences

    rate, amp = 16000, int(32767 * 10 ** (-44 / 20))   # peak at -44 dBFS
    frames = [0] * rate + [int(amp * math.sin(2 * math.pi * 220 * i / rate)) for i in range(3 * rate)] + [0] * rate
    path = tmp_path / "quiet.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", f) for f in frames))
    silences = await detect_silences(path, min_duration=0.25)
    speech = 5.0 - sum(e - s for s, e in silences)
    assert 2.5 < speech < 3.5, silences
