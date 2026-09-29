"""Conversational endpoints used by live sessions and the general coach:
the AI practice partner, the general AI coach, and text-to-speech."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user
from app.config import settings
from app.database import get_db
from app.models.live_session import LiveSession
from app.models.user import User
from app.schemas.live import CoachQuestion, ConversationRequest, TTSRequest
from app.services.ai import get_openai_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversation"])

NO_KEY = "OpenAI API key not configured"

# The live-session AI partner, one persona per practice mode
PARTNER_PROMPTS: dict[str, str] = {
    "Conversation": """\
You are SpeechMate, a warm and encouraging English communication coach.
You are having a SPOKEN conversation with a Malaysian student practising English.

Rules:
- Keep every reply SHORT — 2 to 3 sentences maximum.
- DIRECTLY answer or react to what the user just said, then ask ONE natural follow-up question.
- If you spot a grammar or pronunciation issue, mention it briefly and gently.
- Never give long monologues. Keep the energy conversational and upbeat.
- Do NOT repeat the user's words back at length.""",
    "Interview": """\
You are a professional interviewer conducting a mock job interview for a Malaysian student.

Rules:
- Keep replies to 2-3 sentences.
- Briefly acknowledge their answer (1 sentence of specific feedback).
- Then ask your NEXT interview question — use standard behavioural questions (STAR method, strengths, weaknesses, scenarios, situational).
- Be professional but encouraging.
- Progress through different question types as the conversation continues.""",
    "Presentation": """\
You are a public speaking coach helping a student practise a presentation.

Rules:
- Keep replies SHORT — 2 sentences of coaching, then 1 instruction for what to do next.
- Comment specifically on structure, clarity, signpost language, pace, or audience engagement.
- Guide them through: opening hook → context → main arguments → transitions → conclusion.
- Be constructive and specific.""",
    "Pronunciation": """\
You are a pronunciation coach for a Malaysian English learner.

Rules:
- 1 to 2 sentences only.
- Comment specifically on what was correct and what sound needs work.
- Give ONE concrete tip (tongue position, stress pattern, etc.)
- Be encouraging.""",
}

COACH_PROMPT = """You are SpeechMate AI Coach, an expert communication trainer specializing in:
- Speech fluency and stuttering improvement
- Pronunciation coaching (English and Bahasa Melayu), with Malaysian English treated as a valid accent
- Public speaking and presentation skills
- Communication confidence building
- Eye contact and non-verbal communication

Provide concise, actionable, encouraging feedback. Never shame the user.
Always frame improvements positively and specifically."""

TTS_VOICES = [
    {"id": "nova", "label": "Nova", "desc": "Warm, professional — default coaching voice"},
    {"id": "shimmer", "label": "Shimmer", "desc": "Expressive, conversational"},
    {"id": "alloy", "label": "Alloy", "desc": "Neutral, balanced"},
    {"id": "echo", "label": "Echo", "desc": "Deep, calm"},
    {"id": "fable", "label": "Fable", "desc": "Authoritative, British"},
    {"id": "onyx", "label": "Onyx", "desc": "Deep male voice"},
    {"id": "coral", "label": "Coral", "desc": "Bright, energetic"},
    {"id": "sage", "label": "Sage", "desc": "Thoughtful, measured"},
]


def _client():
    client = get_openai_client()
    if client is None:
        raise HTTPException(status_code=503, detail=NO_KEY)
    return client


@router.post("/chat/message")
async def partner_reply(body: ConversationRequest):
    """The AI partner's next spoken turn in a live session. 503 without an API key
    (the frontend then falls back to scripted prompts)."""
    client = _client()
    system = PARTNER_PROMPTS.get(body.mode, PARTNER_PROMPTS["Conversation"])
    if body.topic:
        system += f"\n\nThe current conversation topic is: {body.topic}"
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "system", "content": system}, *[m.model_dump() for m in body.messages[-12:]]],
            max_tokens=180,
            temperature=0.82,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    return {"reply": (resp.choices[0].message.content or "Could you say that again?").strip()}


async def _user_context(db: AsyncSession, user: User) -> str:
    """The signed-in user's goal and their last few analysed live sessions."""
    recent = (await db.execute(
        select(LiveSession)
        .where(LiveSession.user_id == user.id, LiveSession.status == "complete")
        .order_by(LiveSession.created_at.desc())
        .limit(3)
    )).scalars()
    summaries = [
        {
            "type": s.session_type,
            "date": s.created_at.date().isoformat(),
            "speech": (s.analysis or {}).get("speech"),
            "vision": (s.analysis or {}).get("vision"),
            "overall": (s.analysis or {}).get("communication_score"),
        }
        for s in recent
    ]
    parts = [
        f"Learner: {user.full_name}. Goal: {user.communication_goal or 'not set'}. "
        f"Skill level: {user.skill_level}. Challenges: {', '.join(user.challenges or []) or 'not set'}."
    ]
    if summaries:
        parts.append("Their most recent analysed practice sessions (newest first):\n" + json.dumps(summaries))
    return "\n\n".join(parts)


@router.post("/coach/chat")
async def coach_chat(
    body: CoachQuestion,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """General AI coach. When signed in, it sees your profile and recent session results."""
    client = _client()
    system = COACH_PROMPT
    if user:
        system += "\n\n=== LEARNER CONTEXT ===\n" + await _user_context(db, user)
    messages = [{"role": "system", "content": system}]
    messages += [m.model_dump() for m in body.history[-10:]]
    messages.append({"role": "user", "content": body.question})
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model, messages=messages, max_tokens=500, temperature=0.7
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    return {"answer": (resp.choices[0].message.content or "").strip()}


@router.post("/tts/speak")
async def speak(body: TTSRequest):
    """Stream MP3 speech for the AI partner's replies. 503 without an API key
    (the frontend then falls back to the browser's speech synthesis)."""
    client = _client()
    text = body.text.strip()[:4096]
    voice = body.voice or settings.coach_tts_voice

    async def stream():
        async with client.audio.speech.with_streaming_response.create(
            model=settings.tts_model, voice=voice, input=text, response_format="mp3"
        ) as resp:
            async for chunk in resp.iter_bytes(chunk_size=4096):
                yield chunk

    return StreamingResponse(stream(), media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@router.get("/tts/voices")
async def list_voices():
    return {"voices": TTS_VOICES}
