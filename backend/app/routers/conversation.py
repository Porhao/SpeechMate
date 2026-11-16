"""Conversational endpoints used by live sessions: the AI practice partner (free
conversation, or following an interview / Q&A question plan), speech-to-text and text-to-speech."""

import copy
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_owned, require_cloud_consent
from app.config import settings
from app.database import get_db
from app.models.live_session import LiveSession
from app.models.user import User
from app.schemas.live import ConversationRequest, TTSRequest
from app.limits import MB, rate_limit, read_limited
from app.services import partner
from app.services.ai import get_llm_client, get_openai_client, get_tts_client, track_llm_usage
from app.services.learner import learner_brief
from app.services.live.asr import transcribe_turn

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversation"])

NO_TTS = "No text-to-speech for live replies (set TTS_BASE_URL for a local Kokoro server, or OPENAI_API_KEY)"


@router.post("/chat/message", dependencies=[Depends(rate_limit("chat", 30))])
async def partner_reply(
    body: ConversationRequest,
    user: User = Depends(require_cloud_consent),  # the conversation goes to the cloud LLM
    db: AsyncSession = Depends(get_db),
):
    """The AI partner's next spoken turn. With `live_id`, the session's plan and topic apply and its
    LLM usage is added to the session's tally (reported with its analysis). A free conversation without
    a working LLM is 503 (none configured) or 502; the frontend then falls back to scripted prompts."""
    s = await get_owned(db, LiveSession, body.live_id, user, "Live session") if body.live_id else None
    context = copy.deepcopy(s.context or {}) if s else {}
    with track_llm_usage(context.setdefault("llm_usage", {})):
        reply = await partner.next_line(body.mode, context, [m.model_dump() for m in body.messages], body.topic,
                                        learner_brief(user))
    if reply is None:
        raise HTTPException(status_code=503 if get_llm_client() is None else 502, detail="The AI partner isn't available")
    out = {"reply": reply}
    if s is not None:
        s.context = context
        await db.commit()
        if context.get("plan"):
            out |= {"progress": context.get("progress"), "total_questions": len(context["plan"]["questions"])}
    return out


@router.post("/tts/speak", dependencies=[Depends(rate_limit("tts", 60)), Depends(get_current_user)])
async def speak(body: TTSRequest):
    """Speech for the AI partner's replies when the browser's own Kokoro isn't ready: a local
    Kokoro-style server (TTS_BASE_URL), else OpenAI TTS, else 503 (the frontend then uses the
    browser's voice). Streamed as MP3."""
    local = get_tts_client()
    if local is not None:
        return _stream_speech(local, settings.local_tts_model, settings.local_tts_voice, body.text.strip())

    client = get_openai_client()
    if client is None:
        raise HTTPException(status_code=503, detail=NO_TTS)
    return _stream_speech(client, settings.tts_model, settings.coach_tts_voice, body.text.strip())


def _stream_speech(client, model: str, voice: str, text: str) -> StreamingResponse:
    async def stream():
        async with client.audio.speech.with_streaming_response.create(
            model=model, voice=voice, input=text, response_format="mp3"
        ) as resp:
            async for chunk in resp.iter_bytes(chunk_size=4096):
                yield chunk

    return StreamingResponse(stream(), media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


MAX_STT_BYTES = 15 * MB


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
        return {"text": text}
    finally:
        path.unlink(missing_ok=True)
