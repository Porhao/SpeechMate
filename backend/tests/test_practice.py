"""The three practice functions: interview setup + resume, plan-following AI partner,
deck Q&A plans, content feedback and the extra metrics / pillars (all offline)."""

import io
import zipfile

import httpx
import pytest

from app.database import Base, engine
from app.main import app
from app.services import practice_plans
from app.services.live import coaching, extra_metrics


@pytest.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _sign_in(client, email="cand@example.com"):
    await client.post("/api/auth/register", json={"email": email, "password": "password123", "full_name": "Cand"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _docx(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        paras = "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in text.split("\n"))
        z.writestr("word/document.xml", f"<w:document><w:body>{paras}</w:body></w:document>")
    return buf.getvalue()


# ── Resume ──────────────────────────────────────────────────────────────────

def test_resume_text_from_docx_and_txt():
    assert practice_plans.extract_resume_text(_docx("Aisyah Rahman\nPython, SQL"), "cv.docx") == "Aisyah Rahman\nPython, SQL"
    assert practice_plans.extract_resume_text(b"  Intern  at   Maybank \n\n", "cv.txt") == "Intern at Maybank"
    with pytest.raises(ValueError):
        practice_plans.extract_resume_text(b"x", "cv.png")
    with pytest.raises(ValueError):
        practice_plans.extract_resume_text(b"   ", "cv.txt")


async def test_resume_and_plan_endpoints(client):
    h = await _sign_in(client)
    r = await client.post("/api/interview/resume", headers=h, files={"file": ("cv.docx", _docx("BSc Computer Science"))})
    assert r.status_code == 200 and r.json()["text"] == "BSc Computer Science"
    assert (await client.post("/api/interview/resume", headers=h, files={"file": ("cv.exe", b"MZ")})).status_code == 422
    r = await client.post("/api/interview/plan", headers=h, json={"position": "Software Engineer", "interview_type": "technical"})
    plan = r.json()
    assert r.status_code == 200 and plan["source"] == "rules"
    assert "Software Engineer" in plan["questions"][0]["question"]
    assert plan["questions"][-1]["question"].startswith("Do you have any questions")


# ── The plan-following partner ──────────────────────────────────────────────

async def test_partner_follows_the_interview_plan_without_an_llm(client):
    h = await _sign_in(client)
    r = await client.post("/api/live", headers=h, json={
        "session_type": "Interview", "interview": {"position": "Nurse"},
        "plan": {"intro": "Hi, I'm Alex. Tell me about yourself.",
                 "questions": [{"question": "Tell me about yourself."}, {"question": "Why nursing?"}]},
    })
    lid = r.json()["id"]

    async def say(messages):
        r = await client.post("/api/chat/message", headers=h, json={"messages": messages, "mode": "Interview", "live_id": lid})
        assert r.status_code == 200, r.text
        return r.json()

    first = await say([])
    assert first["reply"] == "Hi, I'm Alex. Tell me about yourself." and first["total_questions"] == 2
    msgs = [{"role": "assistant", "content": first["reply"]}, {"role": "user", "content": "I am a student."}]
    follow = await say(msgs)  # short answer → one follow-up, not the next question
    assert "Why nursing?" not in follow["reply"] and follow["progress"]["followups"] == 1
    msgs += [{"role": "assistant", "content": follow["reply"]}, {"role": "user", "content": "Still short."}]
    nxt = await say(msgs)     # only one follow-up per question
    assert nxt["reply"].endswith("Why nursing?")
    long = " ".join(["I care about patients and I volunteered at a clinic for two years"] * 3)
    msgs += [{"role": "assistant", "content": nxt["reply"]}, {"role": "user", "content": long}]
    assert "That's all the questions" in (await say(msgs))["reply"]


def test_qa_plan_from_deck_insights_fallback():
    insights = {"summary": "Time management for students", "main_message": "Plan your week",
                "likely_questions": ["How do I start?", "What if I fall behind?"],
                "slides": [{"slide_index": 1, "key_point": "Intro"}, {"slide_index": 2, "key_point": "Use a weekly planner"}]}
    plan = practice_plans._fallback_qa_plan("Time Management", insights)
    qs = [q["question"] for q in plan["questions"]]
    assert qs[:2] == ["How do I start?", "What if I fall behind?"]
    assert any("weekly planner" in q for q in qs)
    assert "Time Management" in plan["intro"]


# ── Content feedback ────────────────────────────────────────────────────────

def test_pair_turns_joins_split_answers():
    pairs = practice_plans.pair_turns([
        {"role": "assistant", "text": "Q1"}, {"role": "user", "text": "part one"}, {"role": "user", "text": "part two"},
        {"role": "assistant", "text": "Q2"}, {"role": "assistant", "text": "Q3"}, {"role": "user", "text": "a3"},
    ])
    assert pairs == [{"question": "Q1", "answer": "part one part two"}, {"question": "Q3", "answer": "a3"}]


async def test_rule_based_content_feedback():
    turns = [{"role": "assistant", "text": "Tell me about a challenge you faced."},
             {"role": "user", "text": "When I was at my internship I led a team and as a result we reduced costs by 20%."}]
    fb = await practice_plans.content_feedback("Interview", {"plan": {"questions": []}}, turns)
    a = fb["answers"][0]
    assert fb["source"] == "rules" and a["structure"] >= 4 and a["specificity"] >= 3
    conv = await practice_plans.content_feedback("Conversation", None, [{"role": "assistant", "text": "Hi!"},
                                                                       {"role": "user", "text": "Fine."}])
    assert conv["kind"] == "conversation" and any("Ask a question back" in t for t in conv["tips"])
    assert await practice_plans.content_feedback("Interview", None, []) is None


# ── Extra metrics and pillars ───────────────────────────────────────────────

def test_language_use_metrics():
    r = extra_metrics.analyze_language_use("I think maybe it is kind of good. I think we should, I guess, try it again soon.")
    assert r.hedge_count == 5 and r.top_hedges["i think"] == 2
    assert 0 < r.vocabulary_richness <= 1
    assert extra_metrics.analyze_language_use("too short") is None


def test_metric_scores():
    assert extra_metrics.pace_score(140) == 100 and extra_metrics.pace_score(171) < 75 and extra_metrics.pace_score(200) == 0
    assert extra_metrics.pitch_score(1.0) < 75 <= extra_metrics.pitch_score(3.0)
    assert extra_metrics.latency_score(1.0) == 100 and extra_metrics.latency_score(6.5) == 40


def test_pillars_group_measured_metrics_only():
    analysis = {
        "speech": {"fluency_score": 80, "speaking_rate": 140, "pronunciation_score": None, "filler_per_minute": 4.0},
        "vision": {"eye_contact_score": 60, "posture_score": None, "confidence_score": None},
        "details": {"stuttering": None, "emotion": None},
    }
    lang = extra_metrics.analyze_language_use("We built a dashboard that helped the finance team close reports faster every month.")
    p = extra_metrics.build_pillars(analysis, None, lang, None, {"gaze_tunneling": 0.5})
    assert p["voice"]["score"] == 90.0 and p["voice"]["status"] == "good"
    assert [m["key"] for m in p["language"]["metrics"]] == ["fillers", "vocabulary", "hedging"]
    assert p["body"]["score"] == 60 and p["body"]["status"] == "ok"
    assert p["confidence"]["metrics"][0]["key"] == "gaze_tunneling"


def test_new_metric_recommendations():
    recs = coaching.build_candidates(
        fluency=None, fillers=None, stutter=None, pronunciation=None, eye=None, posture=None, emotion=None,
        duration_sec=120, session_type="Interview",
        prosody={"pitch_variation_st": 1.0, "loudness_dbfs": -42},
        language_use={"hedge_count": 6, "hedges_per_100_words": 4.0, "top_hedges": {"i think": 4}},
        response_latency_sec=5.0,
    )
    assert {r.area for r in recs} == {"vocal_variety", "volume", "hedging", "response_time"}


def test_per_slide_key_point_coverage_drives_feedback():
    from app.services.coach.feedback import rule_based_coach_feedback
    from app.services.coach.metrics import compute_metrics

    m = compute_metrics(
        duration_sec=60, silences=[], transcript="Plan your week with a weekly planner every Sunday.",
        ideal_text="", ideal_duration_sec=None,
        slides=[(1, "Plan the week with a weekly planner every Sunday.", "Use a weekly planner"),
                (2, "Pomodoro technique: focus twenty five minutes then rest.", "Work in focused pomodoro blocks")],
    )
    cov = {c["slide_index"]: c["status"] for c in m["slide_coverage"]}
    assert cov == {1: "covered", 2: "missed"}
    fb = rule_based_coach_feedback(m)
    assert any(o["slide_index"] == 2 and "pomodoro" in o["observation"].lower() for o in fb["observations"])


def test_intro_is_greeting_plus_planned_first_question():
    intro = practice_plans._compose_intro(
        "Hi [Candidate], welcome to our interview today. I'm Alex from Maybank. Let's start with a warm opener: tell me about yourself. Ready?",
        "Can you share a project where you used statistics?", "Aisyah")
    assert intro == "Hi Aisyah, welcome to our interview today. I'm Alex from Maybank. Can you share a project where you used statistics?"
    assert practice_plans._compose_intro("...Welcome, everyone.", "First?", None) == "Welcome, everyone. First?"


def test_invented_terms_flags_new_names_and_numbers_only():
    said = "During my internship I built dashboards in Power BI and we finished two weeks early."
    assert practice_plans.invented_terms("During my internship I built dashboards in Power BI.", said) == []
    assert practice_plans.invented_terms("I used Tableau and cut costs by 30%.", said) == ["Tableau", "30%"]


def test_question_labels_are_removed():
    assert practice_plans._clean_question("Can you share an example? (Role-Specific Problem Solving)") == "Can you share an example?"
    assert practice_plans._clean_question("Do you have any questions for us? (Mixed)") == "Do you have any questions for us?"
    assert practice_plans._clean_question("Why do you use R (not Python) at work?") == "Why do you use R (not Python) at work?"
