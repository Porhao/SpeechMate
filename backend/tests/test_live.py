"""Accounts, live sessions and the live-analysis metrics.

The API test runs with local ML disabled and no API keys, so it exercises the
fallback path: no transcript, pauses/blocks measured from the real audio, and
every model-only metric reported as unavailable (never invented).
"""

import shutil

import httpx
import pytest

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.services import tasks
from app.services.live import language, scoring, speech
from tests.test_e2e import _tone_wav


# ── Pure metric functions ───────────────────────────────────────────────────

def test_language_detection_flags_manglish():
    d = language.detect_language_and_accent("Actually I think the project is good lah, tapi kita perlu more time")
    assert d.primary_language == "mixed"
    assert "lah" in d.manglish_particles
    assert d.malay_ratio > 0
    assert language.detect_language_and_accent("The results were clear and convincing").primary_language == "en"
    assert language.detect_language_and_accent("saya suka makan nasi dengan kawan").primary_language == "ms"


def test_accent_allowance_only_for_malaysian_english():
    en = language.detect_language_and_accent("hello everyone")
    ms = language.detect_language_and_accent("saya suka makan nasi dengan kawan")
    assert language.adjust_pronunciation_for_accent(80.0, en) == 84.0
    assert language.adjust_pronunciation_for_accent(80.0, ms) == 80.0


def test_fluency_from_word_timestamps():
    words = [{"word": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate("one two three four".split())]
    words[3] = {"word": "four", "start": 3.0, "end": 3.4}  # a 1.6 s pause before it
    f = speech.analyze_fluency("one two three four", 4.0, words, silences=[])
    assert f.pause_source == "word_timestamps"
    assert f.pause_frequency == 1
    assert f.longest_pause == 1.6
    assert f.speaking_rate == 60.0


def test_fluency_falls_back_to_audio_silences():
    f = speech.analyze_fluency("a b c d e f", 10.0, [], silences=[(0.0, 0.4), (4.0, 5.0), (9.8, 10.0)])
    assert f.pause_source == "audio"
    assert f.pause_frequency == 1  # edge silences are ignored


def test_fillers_english_and_malay():
    r = speech.detect_fillers("um so basically um the idea lah is you know simple", 60)
    assert r.total_fillers == 5
    assert r.top_filler == "um"
    assert r.filler_breakdown["lah"] == 1


def test_stuttering_repetition_and_block(tmp_path):
    r = speech.detect_stuttering(
        "I I think we should start", [], [(2.0, 3.5)], duration_sec=6.0, wav_16k=tmp_path / "missing.wav"
    )
    assert r.repetition_count == 1
    assert r.block_count == 1
    assert r.stuttering_score == 16.0
    assert r.severity == "Mild"


def test_scores_renormalise_over_available_metrics():
    only_speech = scoring.compute_communication_score(
        {"Fluency": 80, "Pronunciation": None, "Confidence": None, "Eye Contact": None, "Posture": None}
    )
    assert only_speech.overall_score == 80.0
    assert only_speech.scored_on == ["Fluency"]
    assert scoring.compute_communication_score({"Fluency": None}).overall_score is None
    assert scoring.estimate_confidence(
        speaking_rate=None, pause_frequency=None, fluency_score=None, emotion_confidence=None,
        facial_tension=None, posture_score=90, body_stability=70,
    ).confidence_score == 80.0


def test_recommendations_skip_unmeasured_metrics():
    recs = scoring.generate_recommendations(
        fluency=None, pronunciation=None, eye_contact=None, confidence=None, posture=None,
        stuttering=None, filler_count=None, session_history_count=0,
    )
    assert recs.exercises == []
    recs = scoring.generate_recommendations(
        fluency=50, pronunciation=None, eye_contact=40, confidence=None, posture=None,
        stuttering=None, filler_count=12, session_history_count=3,
    )
    assert {e.title for e in recs.exercises} == {"Daily Fluency Drills", "Eye Contact Practice", "Filler Word Elimination"}


# ── API ─────────────────────────────────────────────────────────────────────

@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "use_local_ml", False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _sign_in(client: httpx.AsyncClient, email: str = "aisyah@example.com") -> dict:
    r = await client.post("/api/auth/register", json={
        "full_name": "Aisyah", "email": email, "password": "correct-horse", "communication_goal": "Improve Presentations",
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/auth/login", json={"email": email.upper(), "password": "correct-horse"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_auth_and_profile(client: httpx.AsyncClient):
    assert (await client.get("/api/users/profile")).status_code == 401
    headers = await _sign_in(client)

    r = await client.post("/api/auth/register", json={"full_name": "X", "email": "aisyah@example.com", "password": "12345678"})
    assert r.status_code == 400
    r = await client.post("/api/auth/login", json={"email": "aisyah@example.com", "password": "wrong-password"})
    assert r.status_code == 401

    r = await client.get("/api/users/profile", headers=headers)
    assert r.json()["communication_goal"] == "Improve Presentations"
    r = await client.put("/api/users/profile", headers=headers, json={"skill_level": "Advanced", "challenges": ["Eye Contact"]})
    assert r.json()["skill_level"] == "Advanced"
    assert r.json()["challenges"] == ["Eye Contact"]

    login = await client.post("/api/auth/login", json={"email": "aisyah@example.com", "password": "correct-horse"})
    r = await client.post("/api/auth/refresh", json={"refresh_token": login.json()["refresh_token"]})
    assert r.status_code == 200
    # An access token can't be used as a refresh token
    r = await client.post("/api/auth/refresh", json={"refresh_token": login.json()["access_token"]})
    assert r.status_code == 401


async def test_conversation_endpoints_without_key(client: httpx.AsyncClient):
    r = await client.post("/api/chat/message", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 503
    assert (await client.post("/api/coach/chat", json={"question": "help"})).status_code == 503
    assert (await client.post("/api/tts/speak", json={"text": "hello"})).status_code == 503
    assert len((await client.get("/api/tts/voices")).json()["voices"]) == 8
    # No local model and no key: the frontend falls back to the browser's speech recognition
    r = await client.post("/api/stt", files={"file": ("turn.wav", _tone_wav([(1, True)]))})
    assert r.status_code == 503


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_live_session_analysis_loop(client: httpx.AsyncClient):
    headers = await _sign_in(client)
    other = await _sign_in(client, "someone@example.com")

    r = await client.post("/api/live", headers=headers, json={"session_type": "Presentation"})
    assert r.status_code == 201, r.text
    lid = r.json()["id"]

    # Another user can't see it; analysis needs a recording first
    assert (await client.get(f"/api/live/{lid}", headers=other)).status_code == 404
    assert (await client.post(f"/api/live/{lid}/analyze", headers=headers)).status_code == 409

    recording = _tone_wav([(3, True), (2, False), (3, True)])  # 2 s mid-utterance silence
    r = await client.post(f"/api/live/{lid}/recording", headers=headers, files={"file": ("rec.wav", recording)})
    assert r.status_code == 200 and r.json()["has_recording"]
    r = await client.post(f"/api/live/{lid}/end", headers=headers, json={"duration_sec": 8})
    assert r.json()["duration_sec"] == 8

    r = await client.post(f"/api/live/{lid}/analyze", headers=headers)
    assert r.status_code == 202
    await tasks.wait_for_all(timeout=60)

    live = (await client.get(f"/api/live/{lid}", headers=headers)).json()
    assert live["status"] == "complete", live
    a = live["analysis"]
    # Nothing invented: without ASR or local models these are unavailable…
    assert a["transcript"] is None
    assert a["speech"]["fluency_score"] is None
    assert a["vision"]["eye_contact_score"] is None
    assert a["communication_score"]["overall_score"] is None
    # …but the audio itself was really measured
    assert a["speech"]["stuttering_score"] == 8.0
    assert a["details"]["stuttering"]["block_count"] == 1
    assert any("speech recognition" in w for w in live["warnings"])
    assert any("Vision analysis" in w for w in live["warnings"])

    # No measured scores → no progress points; report still summarises the session
    assert (await client.get("/api/progress", headers=headers)).json() == []
    r = await client.post("/api/reports/generate", headers=headers)
    assert r.status_code == 201
    report = r.json()
    assert report["content"]["totals"]["sessions"] == 1
    assert report["report_url"] == f"/api/reports/{report['id']}"
    assert (await client.get(report["report_url"], headers=headers)).status_code == 200
    assert len((await client.get("/api/reports", headers=headers)).json()) == 1

    history = (await client.get("/api/live", headers=headers)).json()
    assert [h["id"] for h in history] == [lid]
    assert (await client.delete(f"/api/live/{lid}", headers=headers)).status_code == 204
    assert (await client.get("/api/live", headers=headers)).json() == []


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_silent_recording_fails_cleanly(client: httpx.AsyncClient):
    headers = await _sign_in(client)
    lid = (await client.post("/api/live", headers=headers, json={"session_type": "Conversation"})).json()["id"]
    await client.post(f"/api/live/{lid}/recording", headers=headers, files={"file": ("rec.wav", _tone_wav([(3, False)]))})
    await client.post(f"/api/live/{lid}/analyze", headers=headers)
    await tasks.wait_for_all(timeout=60)
    live = (await client.get(f"/api/live/{lid}", headers=headers)).json()
    assert live["status"] == "failed"
    assert "No speech" in live["error_detail"]
