"""Create demo accounts (and example history) for local testing.

Runs at container start after migrations, but only when SEED_DEMO_DATA=true
(the root docker-compose.yml sets it; never enable it in production).
Idempotent: accounts that already exist are left untouched.

    python scripts/seed_demo.py          # respects SEED_DEMO_DATA
    python scripts/seed_demo.py --force  # seed regardless

Accounts (see TESTING.md in the repository root):
    demo@speechmate.dev / Demo1234!   Aisyah — profile filled in + 3 example live sessions
    new@speechmate.dev  / Demo1234!   Farid  — empty account, for first-run flows
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.database import async_session_factory  # noqa: E402
from app.models.live_session import LiveSession, ProgressRecord  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.live import scoring  # noqa: E402

PASSWORD = "Demo1234!"
DEMO_NOTE = "Demo data created by scripts/seed_demo.py — not a real recording."

ACCOUNTS = [
    {
        "email": "demo@speechmate.dev",
        "full_name": "Aisyah Rahman",
        "language": "Bilingual",
        "age_group": "18-24",
        "communication_goal": "Improve Presentations",
        "skill_level": "Intermediate",
        "challenges": ["Eye Contact", "Speaking Pace", "Confidence"],
        "with_history": True,
    },
    {
        "email": "new@speechmate.dev",
        "full_name": "Farid Hakim",
        "language": "en",
        "age_group": None,
        "communication_goal": None,
        "skill_level": "Beginner",
        "challenges": [],
        "with_history": False,
    },
]

# Three sessions over two weeks showing steady improvement
HISTORY = [
    {"days_ago": 13, "type": "Conversation", "duration": 312, "fluency": 61.0, "pron": 72.5, "eye": 58.0,
     "posture": 70.0, "conf": 60.0, "wpm": 168.0, "fillers": 14, "stutter": 16.0, "emotion": "neutral",
     "transcript": "Um, so today I want to, um, talk about my final year project lah. It is basically about "
                   "helping students practise speaking. Actually the idea is, uh, quite simple one."},
    {"days_ago": 7, "type": "Interview", "duration": 405, "fluency": 70.5, "pron": 76.0, "eye": 66.0,
     "posture": 74.0, "conf": 68.5, "wpm": 152.0, "fillers": 8, "stutter": 8.0, "emotion": "neutral",
     "transcript": "My greatest strength is that I stay organised under pressure. For example, during my "
                   "internship I, um, managed three deadlines in the same week by planning each day the night before."},
    {"days_ago": 1, "type": "Presentation", "duration": 540, "fluency": 81.0, "pron": 80.5, "eye": 77.0,
     "posture": 82.0, "conf": 78.0, "wpm": 138.0, "fillers": 3, "stutter": 0.0, "emotion": "happy",
     "transcript": "Good morning everyone. Today I will show how SpeechMate gives accent-fair feedback to "
                   "Malaysian speakers. First, the problem. Second, our approach. And finally, the results."},
]


def _analysis(h: dict, history_count: int) -> dict:
    comm = scoring.compute_communication_score({
        "Fluency": h["fluency"], "Pronunciation": h["pron"], "Confidence": h["conf"],
        "Eye Contact": h["eye"], "Posture": h["posture"],
    })
    recs = scoring.generate_recommendations(
        fluency=h["fluency"], pronunciation=h["pron"], eye_contact=h["eye"], confidence=h["conf"],
        posture=h["posture"], stuttering=h["stutter"], filler_count=h["fillers"],
        session_history_count=history_count,
    )
    minutes = h["duration"] / 60
    manglish = "lah" in h["transcript"]
    return {
        "transcript": h["transcript"],
        "duration_sec": float(h["duration"]),
        "language": {
            "primary_language": "mixed" if manglish else "en",
            "english_ratio": 0.93 if manglish else 1.0,
            "malay_ratio": 0.07 if manglish else 0.0,
            "is_code_switching": False,
            "manglish_particles": ["lah"] if manglish else [],
            "detected_bm_words": ["lah"] if manglish else [],
            "accent_type": "Malaysian English",
        },
        "speech": {
            "fluency_score": h["fluency"], "speaking_rate": h["wpm"], "pronunciation_score": h["pron"],
            "stuttering_score": h["stutter"],
            "stuttering_severity": "None" if h["stutter"] == 0 else "Mild",
            "filler_count": h["fillers"], "filler_per_minute": round(h["fillers"] / minutes, 1),
            "top_filler": "um" if h["fillers"] else "none", "pause_frequency": max(2, h["fillers"] // 2),
            "fluency_grade": "Excellent" if h["fluency"] >= 80 else "Good" if h["fluency"] >= 65 else "Fair",
        },
        "vision": {
            "eye_contact_score": h["eye"], "posture_score": h["posture"], "dominant_emotion": h["emotion"],
            "confidence_score": h["conf"], "confidence_label": "High" if h["conf"] >= 75 else "Medium",
        },
        "communication_score": {
            "overall_score": comm.overall_score, "grade": comm.grade, "strengths": comm.strengths,
            "improvement_areas": comm.improvement_areas, "scored_on": comm.scored_on,
        },
        "recommendations": recs.to_dict(),
        "details": {"asr_engine": "demo-seed"},
    }


async def seed() -> None:
    async with async_session_factory() as db:
        for acc in ACCOUNTS:
            if (await db.execute(select(User).where(User.email == acc["email"]))).scalar_one_or_none():
                print(f"  {acc['email']} already exists — skipped")
                continue
            user = User(
                email=acc["email"], full_name=acc["full_name"], password_hash=hash_password(PASSWORD),
                language=acc["language"], age_group=acc["age_group"],
                communication_goal=acc["communication_goal"], skill_level=acc["skill_level"],
                challenges=acc["challenges"],
            )
            db.add(user)
            await db.flush()

            if acc["with_history"]:
                now = datetime.now(timezone.utc)
                for i, h in enumerate(HISTORY):
                    when = now - timedelta(days=h["days_ago"])
                    analysis = _analysis(h, i + 1)
                    live = LiveSession(
                        user_id=user.id, session_type=h["type"], duration_sec=h["duration"],
                        status="complete", warnings=[DEMO_NOTE], created_at=when,
                    )
                    db.add(live)
                    await db.flush()
                    live.analysis = {"session_id": str(live.id), **analysis}
                    for name, value in {
                        "fluency_score": h["fluency"], "pronunciation_score": h["pron"],
                        "eye_contact_score": h["eye"], "confidence_score": h["conf"],
                        "posture_score": h["posture"],
                        "overall_score": analysis["communication_score"]["overall_score"],
                    }.items():
                        db.add(ProgressRecord(
                            user_id=user.id, live_session_id=live.id, metric_name=name,
                            metric_value=value, recorded_at=when,
                        ))
            print(f"  created {acc['email']}" + (" with 3 example sessions" if acc["with_history"] else ""))
        await db.commit()


if __name__ == "__main__":
    enabled = os.environ.get("SEED_DEMO_DATA", "").lower() in ("1", "true", "yes")
    if not enabled and "--force" not in sys.argv:
        sys.exit(0)
    print("Seeding demo accounts…")
    asyncio.run(seed())
