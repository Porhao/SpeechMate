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
from app.services.live import coaching, language, scoring, speech
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


def test_fluency_ignores_turn_gaps_in_a_conversation():
    # Two answers of 4 words, with the AI talking for 10 s in between
    words = [{"word": "w", "start": t, "end": t + 0.4} for t in (0.0, 0.5, 1.0, 1.5, 12.0, 12.5, 13.0, 13.5)]
    f = speech.analyze_fluency("a b c d e f g h", 14.0, words, silences=[])
    assert f.pause_frequency == 0          # the 10 s turn change is not a hesitation
    assert f.speaking_rate == 123.1        # 8 words over 3.9 s of talking, not 34 wpm over 14 s


def test_fluency_falls_back_to_audio_silences():
    f = speech.analyze_fluency("a b c d e f", 10.0, [], silences=[(0.0, 0.4), (4.0, 5.0), (9.8, 10.0)])
    assert f.pause_source == "audio"
    assert f.pause_frequency == 1  # edge silences are ignored


def test_fillers_english_and_malay():
    r = speech.detect_fillers("Um, so basically, um the idea is, you know, simple. Err macam, sebenarnya okay lah.", 60)
    assert r.filler_breakdown == {"um": 2, "basically": 1, "you know": 1, "err": 1, "macam": 1, "sebenarnya": 1}
    assert r.top_filler == "um" and r.total_fillers == 7


def test_filler_words_need_filler_context():
    # Ordinary uses of "like", "kind of", "right", "tapi" and particles aren't fillers
    r = speech.detect_fillers("I like working with data. What kind of tool is right for you? Tapi kita boleh lah.", 60)
    assert r.total_fillers == 0
    assert speech.count_fillers("Like, I was like, you know, so nervous. Well, it went right.") == {"like": 2, "you know": 1, "well": 1}


def test_stuttering_repetition_and_block(tmp_path):
    r = speech.detect_stuttering(
        "I I think we should start", [], [(2.0, 3.5)], duration_sec=6.0, wav_16k=tmp_path / "missing.wav"
    )
    assert r.repetition_count == 1
    assert r.block_count == 1
    assert r.stuttering_score == 16.0
    assert r.severity == "Mild"
    # A 10 s silence is the AI's turn in a conversation, not a block
    assert speech.detect_stuttering("we should start", [], [(2.0, 12.0)], duration_sec=15.0,
                                    wav_16k=tmp_path / "missing.wav").block_count == 0


def test_scores_renormalise_over_available_metrics():
    only_speech = scoring.compute_communication_score(
        {"Fluency": 80, "Pronunciation": None, "Confidence": None, "Eye Contact": None, "Posture": None}
    )
    assert only_speech.overall_score == 80.0
    assert only_speech.scored_on == ["Fluency"]
    assert scoring.compute_communication_score({"Fluency": None}).overall_score is None
    body = scoring.estimate_confidence(posture_score=90, body_stability=70, eye_contact_score=80)
    assert body.confidence_score == 81.2                    # (90 x 0.11 + 70 x 0.07 + 80 x 0.14) / 0.32
    assert body.speech_confidence is None and body.coverage == 0.32
    # Too little evidence (here 5%: only the response time) gives no score rather than a made-up one
    assert scoring.estimate_confidence(response_latency_sec=2.0) is None


def test_confidence_is_per_minute_not_per_session():
    # The same habits over 1 and over 5 minutes of talking must score the same
    habit = dict(speaking_rate=140, pause_frequency=8, repetition_count=2, block_count=1)
    short = scoring.estimate_confidence(talk_minutes=1, **habit)
    long = scoring.estimate_confidence(talk_minutes=5, **{k: v * 5 if k != "speaking_rate" else v for k, v in habit.items()})
    assert short.confidence_score == long.confidence_score


def test_confidence_uses_every_cue_and_explains_itself():
    c = scoring.estimate_confidence(
        speaking_rate=80, talk_minutes=2, pause_frequency=60, repetition_count=6, block_count=2,
        fillers_per_minute=6, response_latency_sec=4, emotion_confidence=40, facial_tension=60,
        posture_score=50, body_stability=50, eye_contact_score=30,
    )
    assert c.coverage == 1.0 and len(c.cues) == 11
    by = {q["key"]: q["score"] for q in c.cues}
    assert by["pace"] == 40.0                                # 40 wpm too slow x 1.5
    assert by["repetitions"] == 55.0                         # 3 a minute x 15
    assert c.label == "Low" and c.confidence_score < 50
    calm = scoring.estimate_confidence(speaking_rate=140, talk_minutes=2, pause_frequency=8, repetition_count=0,
                                       block_count=0, fillers_per_minute=1, eye_contact_score=85, posture_score=85)
    assert calm.label == "High"


def _candidates(**over):
    base = dict(
        fluency={"speaking_rate": 182.0}, fillers={"total_fillers": 9, "fillers_per_minute": 4.5,
        "filler_breakdown": {"um": 6, "like": 3}, "top_filler": "um"},
        stutter={"detected_events": [
            {"type": "Block", "start_time": 41.0, "end_time": 43.4, "word": ""},
            {"type": "Repetition", "start_time": 5.0, "end_time": 5.6, "word": "i"},
        ]},
        pronunciation=None,
        eye={"eye_contact_score": 52.0, "look_away_percentage": 48.0, "dominant_gaze": "down"},
        posture=None, emotion=None, duration_sec=120.0, session_type="Presentation",
        previous={"speech": {"filler_per_minute": 6.0}},
    )
    return coaching.build_candidates(**{**base, **over})


def test_recommendations_cite_measured_evidence():
    recs = {r.area: r for r in _candidates()}
    assert set(recs) == {"pace", "pauses", "fillers", "eye_contact"}  # 1 repetition isn't enough to flag
    assert "182 words per minute" in recs["pace"].evidence
    assert "0:41" in recs["pauses"].evidence and "2.4 s" in recs["pauses"].evidence
    assert "“um” ×6" in recs["fillers"].evidence
    assert "Better than last session (6/min → 4.5/min)" in recs["fillers"].evidence
    assert "reading notes" in recs["eye_contact"].evidence
    assert "now 4.5" in recs["fillers"].target  # targets are relative to the current value


def test_recommendations_skip_unmeasured_metrics():
    none = coaching.build_candidates(
        fluency=None, fillers=None, stutter=None, pronunciation=None, eye=None, posture=None,
        emotion=None, duration_sec=120.0, session_type="Conversation",
    )
    assert none == []
    plan = coaching.rule_based_plan(none, ["Fluency"], "Conversation", 0)
    assert plan.exercises == [] and "Fluency" in plan.summary


class _FakeLLM:
    """Returns queued replies from chat.completions.create."""
    def __init__(self, replies):
        self.replies = list(replies)
        self.chat = self
        self.completions = self

    async def create(self, **_):
        content = self.replies.pop(0)
        return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": content})()})()]})()


async def test_llm_plan_cannot_invent_unmeasured_issues(monkeypatch):
    import json as _json
    item = lambda area: {"area": area, "title": "Fix it now", "evidence": "measured number 4.5 per minute",
                         "why": "listeners notice this", "drill": "do the drill for five minutes daily", "target": "under 3/min"}
    invented = _json.dumps({"summary": "Good clear voice today.", "focus": [item("vocal_variety")]})
    valid = _json.dumps({"summary": "Good clear voice today.", "focus": [item("fillers"), item("pace")]})
    monkeypatch.setattr(coaching, "get_llm_client", lambda: _FakeLLM([invented, valid]))
    plan = await coaching.build_plan(candidates=_candidates(), strengths=["Posture"], session_type="Presentation",
                                     user_goal=None, session_history_count=1, transcript_excerpt="", warnings=[])
    assert plan.source == "llm"
    assert [e["area"] for e in plan.exercises] == ["fillers", "pace"]


async def test_llm_plan_falls_back_to_measured_plan(monkeypatch):
    monkeypatch.setattr(coaching, "get_llm_client", lambda: _FakeLLM(["not json", "still not json"]))
    plan = await coaching.build_plan(candidates=_candidates(), strengths=[], session_type="Presentation",
                                     user_goal=None, session_history_count=1, transcript_excerpt="", warnings=[])
    assert plan.source == "rules"
    assert len(plan.exercises) == 3 and plan.exercises[0]["evidence"]


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

    # The refresh token is an httpOnly cookie for /api/auth only, never in the body
    login = await client.post("/api/auth/login", json={"email": "aisyah@example.com", "password": "correct-horse"})
    assert login.json().get("refresh_token") is None
    cookie = login.headers["set-cookie"]
    assert "sm_refresh=" in cookie and "HttpOnly" in cookie and "Path=/api/auth" in cookie
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    # Logging out clears it
    await client.post("/api/auth/logout")
    client.cookies.clear()
    assert (await client.post("/api/auth/refresh")).status_code == 401
    # An access token can't be used as a refresh token
    r = await client.post("/api/auth/refresh", json={"refresh_token": login.json()["access_token"]})
    assert r.status_code == 401


async def test_login_is_rate_limited_per_account(client: httpx.AsyncClient):
    await client.post("/api/auth/register", json={"full_name": "B", "email": "b@example.com", "password": "correct-horse"})
    for _ in range(10):
        assert (await client.post("/api/auth/login", json={"email": "b@example.com", "password": "nope-nope"})).status_code == 401
    r = await client.post("/api/auth/login", json={"email": "b@example.com", "password": "correct-horse"})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


async def test_uploads_are_capped_and_partial_files_removed(tmp_path):
    import io

    from fastapi import HTTPException, UploadFile

    from app.limits import read_limited, save_limited

    big = lambda: UploadFile(io.BytesIO(b"x" * 3000), filename="big.webm")  # noqa: E731
    with pytest.raises(HTTPException) as e:
        await read_limited(big(), 2048, "The resume")
    assert e.value.status_code == 413
    dest = tmp_path / "rec.webm"
    with pytest.raises(HTTPException):
        await save_limited(big(), dest, 2048, "The recording")
    assert not dest.exists()
    await save_limited(UploadFile(io.BytesIO(b"ok"), filename="ok.webm"), dest, 2048, "The recording")
    assert dest.read_bytes() == b"ok"


async def test_conversation_endpoints_without_key(client: httpx.AsyncClient):
    r = await client.post("/api/chat/message", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 503
    assert (await client.post("/api/coach/chat", json={"question": "help"})).status_code == 404  # removed
    assert (await client.post("/api/tts/speak", json={"text": "hello"})).status_code == 503
    assert len((await client.get("/api/tts/voices")).json()["voices"]) == 8
    # No local model and no key: the frontend falls back to the browser's speech recognition
    r = await client.post("/api/stt", files={"file": ("turn.wav", _tone_wav([(1, True)]))})
    assert r.status_code == 503


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_live_session_analysis_loop(client: httpx.AsyncClient):
    headers = await _sign_in(client)
    other = await _sign_in(client, "someone@example.com")

    # Interview needs its setup; without an LLM the plan comes from the question bank
    assert (await client.post("/api/live", headers=headers, json={"session_type": "Interview"})).status_code == 422
    r = await client.post("/api/live", headers=headers, json={
        "session_type": "Interview",
        "interview": {"position": "Data Analyst", "company": "Petronas", "interview_type": "behavioural"},
    })
    assert r.status_code == 201, r.text
    lid = r.json()["id"]
    plan = r.json()["context"]["plan"]
    assert plan["source"] == "rules" and "Data Analyst" in plan["intro"]

    # Another user can't see it; analysis needs a recording first
    assert (await client.get(f"/api/live/{lid}", headers=other)).status_code == 404
    assert (await client.post(f"/api/live/{lid}/analyze", headers=headers)).status_code == 409

    recording = _tone_wav([(3, True), (2, False), (3, True)])  # 2 s mid-utterance silence
    r = await client.post(f"/api/live/{lid}/recording", headers=headers, files={"file": ("rec.wav", recording)})
    assert r.status_code == 200 and r.json()["has_recording"]
    turns = [{"role": "assistant", "text": plan["questions"][0]["question"]},
             {"role": "user", "text": "I studied statistics and at my internship I built a dashboard which reduced report time by 30%."}]
    r = await client.post(f"/api/live/{lid}/end", headers=headers,
                          json={"duration_sec": 8, "turns": turns, "client_metrics": {"response_latency_sec": [4.0, 5.0]}})
    assert r.json()["duration_sec"] == 8 and len(r.json()["turns"]) == 2

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
    # The simple view: pillars list only what was measured (here: the browser's response time)
    assert a["pillars"]["voice"]["score"] is None
    assert [m["key"] for m in a["pillars"]["confidence"]["metrics"]] == ["response_time"]
    assert any(e["area"] == "response_time" for e in a["recommendations"]["exercises"])
    # Content feedback judges the answer against the plan (rule-based without an LLM)
    fb = a["content_feedback"]
    assert fb["kind"] == "answers" and fb["source"] == "rules" and len(fb["answers"]) == 1

    # Only measured scores become progress points (here: presence, from the response time)
    assert [p["metric_name"] for p in (await client.get("/api/progress", headers=headers)).json()] == ["presence_score"]
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
