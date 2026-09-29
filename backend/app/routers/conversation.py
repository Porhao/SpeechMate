"""Conversational endpoints used by live sessions and the general coach:
the AI practice partner, the general AI coach, and text-to-speech."""

import asyncio
import json
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user
from app.config import settings
from app.database import get_db
from app.models.live_session import LiveSession
from app.models.user import User
from app.schemas.live import CoachQuestion, ConversationRequest, TTSRequest
from app.services import malaysian_tts
from app.services.ai import get_llm_client, get_openai_client, get_tts_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversation"])

NO_LLM = "No LLM configured (set OPENAI_API_KEY, or LLM_BASE_URL for a local model like Ollama)"
NO_TTS = (
    "No text-to-speech for live replies (set TTS_BASE_URL for a local Kokoro server, OPENAI_API_KEY, "
    "or LIVE_TTS_LOCAL=true for the local Malaysian TTS)"
)

# Replies are spoken aloud, so they must read like natural speech
SPOKEN_STYLE = """

Speak like a real person in a relaxed voice conversation:
- Use contractions and everyday phrasing ("that's great", "let's try", "you know what").
- Vary your sentence length; it's fine to start with a short reaction like "Oh nice!" or "Hmm, good point."
- Plain sentences only: no lists, bullet points, headings, emoji, asterisks or markdown — everything you write is read aloud by a text-to-speech voice.
- Never say you are an AI unless asked."""

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


def _llm():
    client = get_llm_client()
    if client is None:
        raise HTTPException(status_code=503, detail=NO_LLM)
    return client


@router.post("/chat/message")
async def partner_reply(body: ConversationRequest):
    """The AI partner's next spoken turn in a live session. 503 without an API key
    (the frontend then falls back to scripted prompts)."""
    client = _llm()
    system = PARTNER_PROMPTS.get(body.mode, PARTNER_PROMPTS["Conversation"]) + SPOKEN_STYLE
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
    client = _llm()
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


def _local_live_tts() -> bool:
    """Local Malaysian TTS is too slow for conversation on CPU, so by default only use it on a GPU."""
    mode = settings.live_tts_local.lower()
    if mode in ("true", "1", "yes"):
        return malaysian_tts.is_available()
    if mode == "auto" and malaysian_tts.is_available():
        import torch

        return torch.cuda.is_available()
    return False


@router.post("/tts/speak")
async def speak(body: TTSRequest, background: BackgroundTasks):
    """Speech for the AI partner's replies, in order: a local Kokoro-style server (TTS_BASE_URL),
    OpenAI TTS, the local Malaysian TTS (when enabled), else 503 (the frontend then uses the
    browser's voice). Streamed as MP3, except the Malaysian TTS (WAV)."""
    local = get_tts_client()
    if local is not None:
        # The frontend asks for OpenAI's "nova"; Kokoro voice ids look like "af_heart"
        voice = body.voice if body.voice and "_" in body.voice else settings.local_tts_voice
        return _stream_speech(local, settings.local_tts_model, voice, body.text.strip()[:4096])

    client = get_openai_client()
    if client is None:
        if not _local_live_tts():
            raise HTTPException(status_code=503, detail=NO_TTS)
        out = Path(tempfile.mkstemp(suffix=".wav")[1])
        try:
            await asyncio.to_thread(malaysian_tts.synthesize, body.text.strip()[:1000], out, body.voice)
        except Exception as e:  # noqa: BLE001
            out.unlink(missing_ok=True)
            raise HTTPException(status_code=502, detail=f"Local TTS failed: {e}")
        background.add_task(out.unlink, missing_ok=True)
        return FileResponse(out, media_type="audio/wav", headers={"Cache-Control": "no-store"})
    return _stream_speech(client, settings.tts_model, body.voice or settings.coach_tts_voice, body.text.strip()[:4096])


def _stream_speech(client, model: str, voice: str, text: str) -> StreamingResponse:
    async def stream():
        async with client.audio.speech.with_streaming_response.create(
            model=model, voice=voice, input=text, response_format="mp3"
        ) as resp:
            async for chunk in resp.iter_bytes(chunk_size=4096):
                yield chunk

    return StreamingResponse(stream(), media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


# Whisper sometimes "hears" these in near-silence or noise (YouTube-style outros)
_STT_HALLUCINATIONS = (
    "thank you for watching", "thanks for watching", "please subscribe", "subscribe to",
    "see you in the next video", "like and subscribe",
)
STT_PROMPT = "Malaysian English conversation. The speaker may use words like lah, kan, tapi, sebenarnya."
MAX_STT_BYTES = 15 * 1024 * 1024


def _local_stt(path: Path) -> str:
    from app.services.live.asr import _whisper_model, whisper_language

    language = whisper_language()
    segments, _ = _whisper_model().transcribe(
        str(path), language=language, initial_prompt=STT_PROMPT, vad_filter=True,
        condition_on_previous_text=False,
    )
    kept = [
        seg.text.strip() for seg in segments
        if not (seg.no_speech_prob > 0.6 and seg.avg_logprob < -1.0)
        and not any(h in seg.text.lower() for h in _STT_HALLUCINATIONS)
    ]
    return " ".join(t for t in kept if t).strip()


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(..., description="One spoken turn (WAV/WebM)")):
    """Transcribe one conversation turn for the live AI partner: local faster-whisper, else the
    OpenAI API, else 503 (the frontend then falls back to the browser's speech recognition)."""
    from app.services.live._ml import available

    data = await file.read()
    if len(data) > MAX_STT_BYTES:
        raise HTTPException(status_code=413, detail="Recording too long for one turn")
    suffix = Path(file.filename or "turn.wav").suffix or ".wav"
    fd, name = tempfile.mkstemp(suffix=suffix)
    path = Path(name)
    try:
        with open(fd, "wb") as f:
            f.write(data)
        if available("faster_whisper"):
            return {"text": await asyncio.to_thread(_local_stt, path), "engine": "faster-whisper"}
        client = get_openai_client()
        if client is None:
            raise HTTPException(status_code=503, detail="No speech recognition available")
        extra = {} if settings.stt_language == "auto" else {"language": settings.stt_language or "en"}
        with path.open("rb") as f:
            resp = await client.audio.transcriptions.create(
                model=settings.transcription_model, file=f, prompt=STT_PROMPT, **extra
            )
        return {"text": resp.text.strip(), "engine": f"openai:{settings.transcription_model}"}
    finally:
        path.unlink(missing_ok=True)


@router.get("/tts/voices")
async def list_voices():
    return {"voices": TTS_VOICES}
