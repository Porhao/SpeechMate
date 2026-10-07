"""Practice endpoints (Coach Agent) — upload a rehearsal, get OIS feedback, chat."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user
from app.database import get_db
from app.models.chat_message import ChatMessage
from app.models.practice_session import PracticeSession
from app.models.user import User
from app.routers.sessions import audio_extension, get_session_or_404, get_slides
from app.schemas.practice import (
    ChatHistoryResponse,
    ChatMessageOut,
    ChatRequest,
    PracticeCreateResponse,
    PracticeResponse,
)
from app.services import tasks
from app.services.coach.chat import generate_reply
from app.services.coach.pipeline import run_coach_pipeline
from app.limits import MB
from app.services.storage import storage_service

MAX_PRACTICE_BYTES = 300 * MB  # a whole-deck rehearsal recording

router = APIRouter(prefix="/sessions/{session_id}/practice", tags=["practice"])


def _to_response(p: PracticeSession) -> PracticeResponse:
    return PracticeResponse(
        practice_id=p.id,
        session_id=p.session_id,
        status=p.status,
        recording_granularity=p.recording_granularity,
        slide_index=p.slide_index,
        error_detail=p.error_detail,
        warnings=p.warnings or [],
        transcript=p.transcript,
        metrics=p.metrics,
        feedback=p.feedback,
        audience_feedback=p.audience_feedback,
        created_at=p.created_at,
    )


async def _practice_or_404(db: AsyncSession, session_id: uuid.UUID, practice_id: uuid.UUID) -> PracticeSession:
    practice = (await db.execute(
        select(PracticeSession).where(
            PracticeSession.id == practice_id, PracticeSession.session_id == session_id
        )
    )).scalar_one_or_none()
    if not practice:
        raise HTTPException(status_code=404, detail="Practice run not found")
    return practice


@router.post("", response_model=PracticeCreateResponse, status_code=201)
async def create_practice(
    session_id: uuid.UUID,
    audio: UploadFile = File(..., description="Practice recording (audio, or video with audio)"),
    recording_granularity: str = Form("whole_deck", description="whole_deck | per_slide"),
    slide_index: int | None = Form(None, description="Required when recording_granularity=per_slide"),
    db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user),
):
    """Upload a practice recording and start the Coach Agent analysis."""
    session = await get_session_or_404(db, session_id, user)
    if session.status != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"The ideal presentation must be complete before practising (status: {session.status})",
        )
    if recording_granularity not in ("whole_deck", "per_slide"):
        raise HTTPException(status_code=400, detail="recording_granularity must be whole_deck or per_slide")
    if recording_granularity == "per_slide":
        if slide_index is None or not 1 <= slide_index <= (session.slide_count or 0):
            raise HTTPException(
                status_code=400, detail=f"slide_index must be between 1 and {session.slide_count}"
            )
    else:
        slide_index = None

    ext = audio_extension(audio.filename)
    practice_id = uuid.uuid4()
    audio_path = await storage_service.save_upload_limited(
        str(session_id), f"practice/{practice_id}/user_audio_upload{ext}", audio, MAX_PRACTICE_BYTES, "The practice recording"
    )

    db.add(PracticeSession(
        id=practice_id,
        session_id=session_id,
        audio_storage_path=audio_path,
        recording_granularity=recording_granularity,
        slide_index=slide_index,
        status="queued",
    ))
    await db.commit()

    tasks.spawn(run_coach_pipeline(practice_id), name=f"coach-{practice_id}")
    return PracticeCreateResponse(practice_id=practice_id, status="queued")


@router.get("", response_model=list[PracticeResponse])
async def list_practice(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """All practice runs for a session, oldest first (for progress over time)."""
    await get_session_or_404(db, session_id, user)
    result = await db.execute(
        select(PracticeSession)
        .where(PracticeSession.session_id == session_id)
        .order_by(PracticeSession.created_at)
    )
    return [_to_response(p) for p in result.scalars()]


@router.get("/{practice_id}", response_model=PracticeResponse)
async def get_practice(session_id: uuid.UUID, practice_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Poll a practice run; metrics + feedback appear once status is `complete`."""
    await get_session_or_404(db, session_id, user)
    return _to_response(await _practice_or_404(db, session_id, practice_id))


@router.get("/{practice_id}/chat", response_model=ChatHistoryResponse)
async def get_chat(session_id: uuid.UUID, practice_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Chat history for a practice run."""
    await get_session_or_404(db, session_id, user)
    await _practice_or_404(db, session_id, practice_id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.practice_session_id == practice_id)
        .order_by(ChatMessage.created_at)
    )
    return ChatHistoryResponse(messages=[
        ChatMessageOut(role=m.role, content=m.content, created_at=m.created_at) for m in result.scalars()
    ])


@router.post("/{practice_id}/chat", response_model=ChatMessageOut)
async def post_chat(
    session_id: uuid.UUID,
    practice_id: uuid.UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user),
):
    """Ask the Coach Agent a follow-up question about this practice run."""
    session = await get_session_or_404(db, session_id, user)
    practice = await _practice_or_404(db, session_id, practice_id)
    if practice.status != "complete":
        raise HTTPException(status_code=409, detail=f"Feedback is not ready yet (status: {practice.status})")

    history = list((await db.execute(
        select(ChatMessage)
        .where(ChatMessage.practice_session_id == practice_id)
        .order_by(ChatMessage.created_at)
    )).scalars())
    earlier = list((await db.execute(
        select(PracticeSession)
        .where(
            PracticeSession.session_id == session_id,
            PracticeSession.status == "complete",
            PracticeSession.created_at < practice.created_at,
        )
        .order_by(PracticeSession.created_at)
    )).scalars())

    reply = await generate_reply(
        session=session,
        slides=await get_slides(db, session_id),
        practice=practice,
        earlier_attempts=earlier,
        history=history,
        user_message=body.message,
    )

    db.add(ChatMessage(practice_session_id=practice_id, role="user", content=body.message))
    await db.flush()  # keeps created_at ordering user → assistant
    assistant = ChatMessage(practice_session_id=practice_id, role="assistant", content=reply)
    db.add(assistant)
    await db.commit()
    return ChatMessageOut(role="assistant", content=reply, created_at=assistant.created_at)
