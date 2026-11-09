"""Mate, the in-app assistant: answers questions about using SpeechMate, explains the user's own
results, and gives short speaking advice. One Gemini call per message, with a fixed guide to the
app, the learner brief (services/learner.py), a summary of their recent sessions (scores,
pillars, the focus each report gave) and the page they're on. Nothing is stored: the browser
sends the conversation each time and keeps it only while the tab is open.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.live_session import LiveSession
from app.models.user import User
from app.services.ai import get_llm_client
from app.services.learner import learner_brief, with_brief

logger = logging.getLogger(__name__)

RECENT = 5
STATUS = {"active": "not finished (no report)", "analyzing": "report being prepared",
          "failed": "analysis failed (no report)", "complete": "no overall score"}
MAX_TURNS = 12   # the conversation sent to the model: the latest turns only

GUIDE = """You are Mate, the friendly companion inside SpeechMate, a speaking coach for Malaysian students and
young professionals. Answer in 1-4 short sentences (bullets only for steps), plain everyday English, warm but
not gushing; don't greet them or use their name in every reply. You help with three things: how to use SpeechMate, what their own results mean, and practical
speaking advice (nerves, structure, interviews, presentations, fillers, pace, eye contact).
Stay on those; for anything else, say kindly that you can only help with speaking and SpeechMate.
Never invent their scores or sessions: use only the summary below, and say so if there isn't one yet.
Malaysian English and mixing in Malay ("lah", "kan") are fine and never counted as errors.
When pointing to a page, write its path exactly as listed so it becomes a link.

The app (pages):
- /home: today's tasks (drills from your last reports, decks to present), recent sessions.
- /conversation: chat with an AI partner about an everyday topic for 3-5 minutes.
- /interview: a mock interview from your role, background and resume; feedback on every answer with a
  stronger version built from your own facts.
- /presentations: upload slides (.pptx or .pdf); the AI reads them (summary, key point per slide). Then
  "Present it" (you move through your slides on camera; each slide's talk is checked against the slide) or
  "Rehearse the Q&A" (audience questions from your deck).
- /script: write a talk script from a deck for a chosen number of minutes (full script or talking points),
  then "Practise this script".
- /progress: all sessions, scores over time; each opens its report at /results/<id>.
- /profile: study level, field, goals, feedback style (the AI adapts to them). /settings: theme, text size.
- /privacy: what's recorded, where it goes, download or delete your data. /methodology: how each score is measured.
How a session works: nothing is scored while you talk; afterwards the report gives four pillars (Voice &
delivery, Language & clarity, Body language, Confidence & presence), each 0-100 (75+ good, 55-74 okay, below
needs work), the transcript, and three drills to practise next. Speech-to-text is Whisper; the AI is Gemini.
"""


def _session_line(s: LiveSession) -> str:
    a, c = s.analysis or {}, s.context or {}
    kind = "Presentation talk" if c.get("kind") == "talk" else "Presentation Q&A" if c.get("kind") == "qa" else s.session_type
    what = c.get("deck_title") or (c.get("setup") or {}).get("position") or c.get("topic") or ""
    score = (a.get("communication_score") or {}).get("overall_score")
    pillars = ", ".join(f"{p['label']} {p['score']:.0f}" for p in (a.get("pillars") or {}).values()
                        if isinstance(p, dict) and p.get("score") is not None)
    drills = "; ".join(e.get("title", "") for e in ((a.get("recommendations") or {}).get("exercises") or [])[:3])
    parts = [f"{s.created_at:%d %b}", kind + (f" ({what})" if what else ""),
             f"overall {score:.0f}/100" if score is not None else STATUS.get(s.status, s.status)]
    if pillars:
        parts.append(pillars)
    if drills:
        parts.append(f"drills: {drills}")
    return " · ".join(parts)


async def _context(db: AsyncSession, user: User, page: str | None) -> str:
    rows = (await db.execute(select(LiveSession).where(LiveSession.user_id == user.id)
                             .order_by(LiveSession.created_at.desc()).limit(RECENT))).scalars().all()
    lines = [f"The user's first name: {user.full_name.split()[0]}." if user.full_name else ""]
    lines.append("Their latest sessions (newest first):\n" + "\n".join(f"- {_session_line(s)}" for s in rows)
                 if rows else "They haven't done a session yet.")
    if page:
        lines.append(f"They are on the page {page}.")
    return "\n".join(x for x in lines if x)


async def reply(db: AsyncSession, user: User, messages: list[dict], page: str | None) -> str:
    client = get_llm_client()
    if client is None:
        return ("I can't reach the AI right now, so I can only point the way: /methodology explains every score, "
                "and /progress has all your reports.")
    system = with_brief(f"{GUIDE}\n{await _context(db, user, page)}", learner_brief(user))
    convo = [{"role": m["role"], "content": m["text"]} for m in messages[-MAX_TURNS:]]
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model, messages=[{"role": "system", "content": system}, *convo],
            temperature=0.5, max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        logger.error("Mate's reply failed: %s", e)
        text = ""
    return text or "Sorry, I lost my train of thought there. Could you ask that again?"
