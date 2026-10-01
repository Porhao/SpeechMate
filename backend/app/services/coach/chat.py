"""Coach Agent Stage 3: conversational follow-up.

Context per turn: the deck's ideal scripts, this attempt's metrics/feedback/
transcript, a summary of the user's *earlier* attempts on the same deck (so
advice can build on progress, as in the paper), and recent chat history.
"""

import json
import logging

from app.config import settings
from app.models.chat_message import ChatMessage
from app.models.practice_session import PracticeSession
from app.models.session import Session
from app.models.slide import Slide
from app.services.ai import get_llm_client, with_retries
from app.services.deck_insights import coach_context

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20

CHAT_SYSTEM = """You are the Coach Agent of a presentation-practice app, chatting with a learner about their practice run.
Be warm, specific and practical. Ground answers in the context below (metrics, feedback, transcript, ideal script).
If asked for an example, write out the exact words they could say. Keep replies under ~150 words unless asked for more.
You only analysed audio — don't claim to have seen body language or slides being presented.

=== CONTEXT ===
{context}"""


def _attempt_summary(p: PracticeSession) -> dict:
    m = p.metrics or {}
    return {
        "attempt_at": p.created_at.isoformat() if p.created_at else None,
        "slide": p.slide_index if p.recording_granularity == "per_slide" else "whole deck",
        "wpm": m.get("wpm"),
        "filler_word_count": m.get("filler_word_count"),
        "long_pauses": len(m.get("long_pauses") or []),
        "script_coverage": m.get("script_coverage"),
        "main_issues": [o.get("observation") for o in (p.feedback or {}).get("observations", [])],
    }


def build_chat_context(
    session: Session,
    slides: list[Slide],
    practice: PracticeSession,
    earlier_attempts: list[PracticeSession],
) -> str:
    parts = [
        f"Presenter's goal/audience: {session.requirement_prompt or 'not specified'}",
        coach_context(session.insights) or "Deck insights: not available",
        "Ideal narration script:\n" + "\n".join(f"[Slide {s.slide_index}] {s.script_text}" for s in slides),
        f"This attempt ({practice.recording_granularity}"
        + (f", slide {practice.slide_index}" if practice.slide_index else "")
        + "):",
        "Metrics: " + json.dumps(practice.metrics or {}),
        "Coach feedback: " + json.dumps(practice.feedback or {}),
        "Audience reaction: " + json.dumps(practice.audience_feedback or {}),
        "Transcript: " + (practice.transcript or "(not available)"),
    ]
    if earlier_attempts:
        parts.append(
            "Earlier attempts on this deck (oldest first), use these to comment on progress:\n"
            + "\n".join(json.dumps(_attempt_summary(p)) for p in earlier_attempts)
        )
    return "\n\n".join(parts)


def _offline_reply(practice: PracticeSession) -> str:
    fb = practice.feedback or {}
    tips = [o.get("suggestion") for o in fb.get("observations", []) if o.get("suggestion")]
    reply = (
        "Chat needs an LLM (set OPENAI_API_KEY, or LLM_BASE_URL for a local model like Ollama, in .env and restart). "
        "Meanwhile, here are your key suggestions from this attempt:"
    )
    return reply + "".join(f"\n- {t}" for t in tips) if tips else reply


async def generate_reply(
    *,
    session: Session,
    slides: list[Slide],
    practice: PracticeSession,
    earlier_attempts: list[PracticeSession],
    history: list[ChatMessage],
    user_message: str,
) -> str:
    client = get_llm_client()
    if client is None:
        return _offline_reply(practice)

    context = build_chat_context(session, slides, practice, earlier_attempts)
    messages = [{"role": "system", "content": CHAT_SYSTEM.format(context=context)}]
    messages += [{"role": m.role, "content": m.content} for m in history[-MAX_HISTORY_MESSAGES:]]
    messages.append({"role": "user", "content": user_message})

    async def call() -> str:
        resp = await client.chat.completions.create(
            model=settings.llm_model, messages=messages, temperature=0.6
        )
        return (resp.choices[0].message.content or "").strip()

    try:
        reply = await with_retries(call, attempts=2, label="Coach chat")
        return reply or "Sorry, I couldn't come up with an answer — could you rephrase that?"
    except Exception as e:  # noqa: BLE001
        logger.error("Coach chat failed: %s", e)
        return f"Sorry, the coach is unavailable right now ({e}). Please try again in a moment."
