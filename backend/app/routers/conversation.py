"""Conversational endpoints used by live sessions: the AI practice partner (free
conversation, or following an interview / Q&A question plan), speech-to-text and text-to-speech."""

import copy
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_cloud_consent
from app.config import settings
from app.database import get_db
from app.models.live_session import LiveSession
from app.models.user import User
from app.schemas.live import ConversationMessage, ConversationRequest, TTSRequest
from app.limits import rate_limit, read_limited
from app.services import practice_plans
from app.services.ai import get_llm_client, get_openai_client, get_tts_client, track_llm_usage
from app.services.learner import learner_brief, with_brief
from app.services.live.asr import transcribe_turn

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversation"])

NO_LLM = "No LLM configured (set OPENAI_API_KEY, or LLM_BASE_URL for a local model like Ollama)"
NO_TTS = "No text-to-speech for live replies (set TTS_BASE_URL for a local Kokoro server, or OPENAI_API_KEY)"

# Replies are spoken aloud, so they must read like natural speech
SPOKEN_STYLE = """

Speak like a real person in a relaxed voice conversation:
- Use contractions and everyday phrasing ("that's great", "let's try", "you know what").
- Vary your sentence length; it's fine to start with a short reaction like "Oh nice!" or "Hmm, good point."
- Plain sentences only: no lists, bullet points, headings, emoji, asterisks or markdown — everything you write is read aloud by a text-to-speech voice.
- Never say you are an AI unless asked."""

# The live-session AI partner, one persona per practice mode (edit the wording in the text files)
_PROMPTS = Path(__file__).parent.parent / "prompts"
PARTNER_PROMPTS: dict[str, str] = {
    mode: (_PROMPTS / name).read_text(encoding="utf-8").strip()
    for mode, name in {
        "Conversation": "conversation_partner.txt",
        "Interview": "interview_partner.txt",
        "Presentation": "qa_moderator.txt",
    }.items()
}


def _llm():
    client = get_llm_client()
    if client is None:
        raise HTTPException(status_code=503, detail=NO_LLM)
    return client


@router.post("/chat/message", dependencies=[Depends(rate_limit("chat", 30))])
async def partner_reply(
    body: ConversationRequest,
    user: User = Depends(require_cloud_consent),  # the conversation goes to the cloud LLM
    db: AsyncSession = Depends(get_db),
):
    """The AI partner's next spoken turn in a live session.

    With `live_id` of an Interview / Presentation session, it follows that session's
    curated question plan (and works without an LLM). Otherwise it's a free conversation:
    503 without an LLM (the frontend then falls back to scripted prompts)."""
    s = None
    if body.live_id:
        s = (await db.execute(
            select(LiveSession).where(LiveSession.id == body.live_id, LiveSession.user_id == user.id)
        )).scalar_one_or_none()
        if s and s.context and s.context.get("plan"):
            context = copy.deepcopy(s.context)
            with track_llm_usage(context.setdefault("llm_usage", {})):
                reply = await practice_plans.planned_reply(s.session_type, context, [m.model_dump() for m in body.messages])
            s.context = context
            await db.commit()
            return {"reply": reply, "progress": context.get("progress"),
                    "total_questions": len(context["plan"]["questions"])}
        if s and s.context and s.context.get("topic") and not body.topic:
            body.topic = s.context["topic"]
    client = _llm()
    if not body.messages:
        body.messages = [ConversationMessage(role="user", content="(The learner has just joined. Greet them warmly and open the conversation.)")]
    system = with_brief(PARTNER_PROMPTS.get(body.mode, PARTNER_PROMPTS["Conversation"]) + SPOKEN_STYLE, learner_brief(user))
    if body.topic:
        system += f"\n\nThe current conversation topic is: {body.topic}"
    try:
        with track_llm_usage() as used:
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "system", "content": system}, *[m.model_dump() for m in body.messages[-12:]]],
                max_tokens=180,
                temperature=0.82,
            )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    if s is not None:  # the session's running LLM tally (reported with its analysis)
        context = copy.deepcopy(s.context or {})
        tally = context.setdefault("llm_usage", {})
        for k, v in used.items():
            tally[k] = tally.get(k, 0) + v
        s.context = context
        await db.commit()
    return {"reply": (resp.choices[0].message.content or "Could you say that again?").strip()}


@router.post("/tts/speak", dependencies=[Depends(rate_limit("tts", 60)), Depends(get_current_user)])
async def speak(body: TTSRequest):
    """Speech for the AI partner's replies when the browser's own Kokoro isn't ready: a local
    Kokoro-style server (TTS_BASE_URL), else OpenAI TTS, else 503 (the frontend then uses the
    browser's voice). Streamed as MP3."""
    local = get_tts_client()
    if local is not None:
        # The frontend asks for OpenAI's "nova"; Kokoro voice ids look like "af_heart"
        voice = body.voice if body.voice and "_" in body.voice else settings.local_tts_voice
        return _stream_speech(local, settings.local_tts_model, voice, body.text.strip()[:4096])

    client = get_openai_client()
    if client is None:
        raise HTTPException(status_code=503, detail=NO_TTS)
    return _stream_speech(client, settings.tts_model, body.voice or settings.coach_tts_voice, body.text.strip()[:4096])


def _stream_speech(client, model: str, voice: str, text: str) -> StreamingResponse:
    async def stream():
        async with client.audio.speech.with_streaming_response.create(
            model=model, voice=voice, input=text, response_format="mp3"
        ) as resp:
            async for chunk in resp.iter_bytes(chunk_size=4096):
                yield chunk

    return StreamingResponse(stream(), media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


MAX_STT_BYTES = 15 * 1024 * 1024


@router.post("/stt", dependencies=[Depends(rate_limit("stt", 60)), Depends(require_cloud_consent)])
async def speech_to_text(
    file: UploadFile = File(..., description="One spoken turn (WAV/WebM)"),
    context: str | None = Form(None, max_length=1000, description="What the turn answers (the AI's last line, the role…): helps topic words"),
):
    """Transcribe one conversation turn for the live AI partner with the OpenAI-compatible API
    (e.g. Groq): 503 without one (the frontend then lets the user type), 502 when the provider
    fails (the frontend retries)."""
    if get_openai_client() is None:
        raise HTTPException(status_code=503, detail="No speech recognition available")
    data = await read_limited(file, MAX_STT_BYTES, "One spoken turn")
    fd, name = tempfile.mkstemp(suffix=Path(file.filename or "turn.wav").suffix or ".wav")
    path = Path(name)
    try:
        with open(fd, "wb") as f:
            f.write(data)
        try:
            text = await transcribe_turn(path, context)
        except Exception as e:  # rate limit, timeout, provider error
            logger.warning("STT turn failed: %s", e)
            raise HTTPException(status_code=502, detail="Speech recognition failed, please try again") from e
        return {"text": text, "engine": f"openai:{settings.transcription_model}"}
    finally:
        path.unlink(missing_ok=True)
