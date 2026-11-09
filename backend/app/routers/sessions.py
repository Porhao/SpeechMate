"""Deck endpoints: upload a presentation, poll its preparation, fetch slide images."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_cloud_consent
from app.database import get_db
from app.limits import MB, rate_limit
from app.models.session import SESSION_IN_PROGRESS_STATUSES, Session
from app.models.slide import Slide
from app.models.user import User
from app.schemas.session import ScriptRequest, SessionCreateResponse, SessionListItem, SessionStatusResponse
from app.services import tasks
from app.services.learner import learner_brief
from app.services.pipeline import run_ideal_presentation_pipeline
from app.services.script_writer import write_script
from app.services.storage import storage_service

MAX_DECK_BYTES = 100 * MB         # image-heavy PowerPoints get big

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def get_session_or_404(db: AsyncSession, session_id: uuid.UUID, user: User) -> Session:
    """The caller's deck; anyone else's gets 404, as if it didn't exist."""
    session = (await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user.id)
    )).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    pptx: UploadFile = File(..., description="The deck: PowerPoint .pptx or .pdf"),
    requirement_prompt: str | None = Form(None, description="Audience/purpose context (optional)"),
    user: User = Depends(require_cloud_consent),  # the deck's text goes to the cloud LLM
    db: AsyncSession = Depends(get_db),
):
    """Upload a deck and start preparing it. Returns `queued`; poll `GET /api/sessions/{id}`."""
    deck_ext = Path(pptx.filename or "").suffix.lower()
    if deck_ext not in (".pptx", ".pdf"):
        raise HTTPException(status_code=400, detail="The deck must be a PowerPoint (.pptx) or PDF (.pdf) file")

    session_id = uuid.uuid4()
    pptx_path = await storage_service.save_upload_limited(str(session_id), f"original{deck_ext}", pptx, MAX_DECK_BYTES, "The deck")
    db.add(Session(
        id=session_id,
        original_filename=pptx.filename,
        pptx_storage_path=pptx_path,
        requirement_prompt=(requirement_prompt or "").strip() or None,
        user_id=user.id,
        status="queued",
    ))
    await db.commit()  # must be committed before the background job reads it

    tasks.spawn(run_ideal_presentation_pipeline(session_id), name=f"deck-{session_id}")
    logger.info("Session %s created for '%s'", session_id, pptx.filename)
    return SessionCreateResponse(session_id=session_id, status="queued")


@router.get("", response_model=list[SessionListItem])
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Your decks, most recent first."""
    result = await db.execute(select(Session).where(Session.user_id == user.id).order_by(Session.created_at.desc()))
    return [
        SessionListItem(session_id=s.id, original_filename=s.original_filename, status=s.status,
                        slide_count=s.slide_count, created_at=s.created_at)
        for s in result.scalars()
    ]


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Poll a deck's preparation status, with how many slides are rendered so far."""
    session = await get_session_or_404(db, session_id, user)
    rendered = await db.scalar(select(func.count()).select_from(Slide).where(Slide.session_id == session_id))
    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        slide_count=session.slide_count,
        slides_rendered=rendered or 0,
        error_detail=session.error_detail,
        warnings=session.warnings or [],
        original_filename=session.original_filename,
        insights=session.insights,
        script=session.script,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


async def deck_slides(db: AsyncSession, deck: Session) -> list[dict]:
    """Each slide's title, text and key point (from the insights), in order."""
    insights = deck.insights or {}
    points = {p.get("slide_index"): p.get("key_point") for p in insights.get("slides") or []}
    titles = {p.get("slide_index"): p.get("title") for p in (insights.get("stats") or {}).get("per_slide") or []}
    rows = (await db.execute(select(Slide).where(Slide.session_id == deck.id).order_by(Slide.slide_index))).scalars()
    return [{"index": s.slide_index, "title": titles.get(s.slide_index) or "", "text": (s.slide_text or "")[:1500],
             "key_point": points.get(s.slide_index) or ""} for s in rows]


@router.post("/{session_id}/script", dependencies=[Depends(rate_limit("script", 6))])
async def write_deck_script(session_id: uuid.UUID, body: ScriptRequest, db: AsyncSession = Depends(get_db),
                            user: User = Depends(require_cloud_consent)):
    """Write (or rewrite) the deck's practice script for `minutes`; it replaces the previous one."""
    session = await get_session_or_404(db, session_id, user)
    if not session.insights:
        raise HTTPException(status_code=409, detail="Wait until the deck has been read, then write its script")
    slides = await deck_slides(db, session)
    if not slides:
        raise HTTPException(status_code=409, detail="This deck has no slides")
    session.script = await write_script(slides, body.minutes, body.style, session.requirement_prompt, learner_brief(user))
    await db.commit()
    return session.script


@router.post("/{session_id}/retry", response_model=SessionCreateResponse, status_code=202)
async def retry_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_cloud_consent)):
    """Prepare a failed (or completed) deck again."""
    session = await get_session_or_404(db, session_id, user)
    if session.status in SESSION_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail=f"Session is still running ({session.status})")
    session.status = "queued"
    session.error_detail = None
    await db.commit()
    tasks.spawn(run_ideal_presentation_pipeline(session_id), name=f"deck-retry-{session_id}")
    return SessionCreateResponse(session_id=session_id, status="queued")


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete a deck, its slides and all stored files."""
    session = await get_session_or_404(db, session_id, user)
    if session.status in SESSION_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="Wait for the pipeline to finish before deleting")
    await db.delete(session)
    await db.commit()
    storage_service.delete_session(str(session_id))


@router.get("/{session_id}/slides/{slide_index}/image")
async def get_slide_image(session_id: uuid.UUID, slide_index: int, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    """A slide's rendered PNG (the frontend fetches it with the Bearer token: components/presentation/SlideImage)."""
    await get_session_or_404(db, session_id, user)
    slide = (await db.execute(
        select(Slide).where(Slide.session_id == session_id, Slide.slide_index == slide_index)
    )).scalar_one_or_none()
    path = storage_service.get_absolute_path(slide.png_storage_path) if slide and slide.png_storage_path else None
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Slide image not available")
    return FileResponse(path=str(path), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})
