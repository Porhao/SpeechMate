"""Session endpoints (Ideal Presentation Agent) — upload, status polling, artifacts."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.auth import get_optional_user
from app.database import get_db
from app.models.session import SESSION_IN_PROGRESS_STATUSES, Session
from app.models.slide import Slide
from app.models.user import User
from app.schemas.session import (
    SessionCreateResponse,
    SessionListItem,
    SessionStatusResponse,
    SlidesProgress,
)
from app.schemas.slide import SlideScript, SlideScriptsResponse
from app.limits import MB
from app.services import malaysian_tts, tasks
from app.services.media import SLIDE_GAP_SEC
from app.services.pipeline import run_ideal_presentation_pipeline
from app.services.storage import storage_service

MAX_DECK_BYTES = 100 * MB         # image-heavy PowerPoints get big
MAX_VOICE_SAMPLE_BYTES = 25 * MB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])
voices_router = APIRouter(tags=["sessions"])


@voices_router.get("/narrator-voices")
async def narrator_voices():
    """Voices for the presentation narration, and whether the local Malaysian TTS is installed.
    Without a GPU the Malaysian TTS takes minutes per slide, so the fast Kokoro voice is the default there."""
    gpu = malaysian_tts.is_available() and malaysian_tts.keep_loaded()
    slow = "" if gpu else " (slow on this computer: several minutes per slide)"
    return {
        "available": malaysian_tts.is_available(),
        "default": settings.malaysian_tts_voice if gpu else malaysian_tts.FAST_VOICE,
        "voices": [{"id": malaysian_tts.FAST_VOICE, "label": "Fast voice (Kokoro, English): ready in about a minute"}]
                  + [{"id": k, "label": f"Malaysian: {v}{slow}"} for k, v in malaysian_tts.VOICES.items()],
    }

AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".oga", ".flac", ".aac", ".mp4", ".mov"}


def audio_extension(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext or '?'}'. Use one of: {', '.join(sorted(AUDIO_EXTENSIONS))}",
        )
    return ext


async def get_session_or_404(db: AsyncSession, session_id: uuid.UUID, user: User | None) -> Session:
    """The deck, if this caller may see it: a deck with an owner is only visible to that owner
    (anyone else gets 404, as if it didn't exist). Decks uploaded while signed out have no owner
    and are reachable by their unguessable id. Slide images are served by id alone (an <img> can't
    send the Bearer token); see docs/project/Security.md."""
    session = (await db.execute(select(Session).where(Session.id == session_id))).scalar_one_or_none()
    if not session or (session.user_id is not None and (user is None or user.id != session.user_id)):
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def get_slides(db: AsyncSession, session_id: uuid.UUID) -> list[Slide]:
    result = await db.execute(
        select(Slide).where(Slide.session_id == session_id).order_by(Slide.slide_index)
    )
    return list(result.scalars())


@router.post("", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    pptx: UploadFile = File(..., description="The deck: PowerPoint .pptx or .pdf"),
    voice_sample: UploadFile | None = File(None, description="Voice sample for cloning (optional)"),
    requirement_prompt: str | None = Form(None, description="Audience/purpose context (optional)"),
    narrator_voice: str | None = Form(None, description="Malaysian TTS voice id (see GET /api/narrator-voices)"),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new presentation session and start the Ideal Presentation Agent.

    Returns immediately with `queued`; poll `GET /api/sessions/{id}` for progress.
    """
    deck_ext = Path(pptx.filename or "").suffix.lower()
    if deck_ext not in (".pptx", ".pdf"):
        raise HTTPException(status_code=400, detail="The deck must be a PowerPoint (.pptx) or PDF (.pdf) file")

    if narrator_voice and narrator_voice not in {*malaysian_tts.VOICES, malaysian_tts.FAST_VOICE}:
        raise HTTPException(
            status_code=400, detail=f"Unknown narrator_voice. Use one of: {', '.join([malaysian_tts.FAST_VOICE, *malaysian_tts.VOICES])}"
        )

    voice_ext = None
    if voice_sample and voice_sample.filename:
        voice_ext = audio_extension(voice_sample.filename)

    session_id = uuid.uuid4()
    pptx_path = await storage_service.save_upload_limited(str(session_id), f"original{deck_ext}", pptx, MAX_DECK_BYTES, "The deck")

    voice_path = None
    if voice_ext:
        # Keep the real extension; the pipeline converts it to WAV
        voice_path = await storage_service.save_upload_limited(
            str(session_id), f"voice_sample_upload{voice_ext}", voice_sample, MAX_VOICE_SAMPLE_BYTES, "The voice sample"
        )

    session = Session(
        id=session_id,
        original_filename=pptx.filename,
        pptx_storage_path=pptx_path,
        voice_sample_storage_path=voice_path,
        requirement_prompt=(requirement_prompt or "").strip() or None,
        narrator_voice=narrator_voice or None,
        user_id=user.id if user else None,
        status="queued",
    )
    db.add(session)
    await db.commit()  # must be committed before the background job reads it

    tasks.spawn(run_ideal_presentation_pipeline(session_id), name=f"ideal-{session_id}")
    logger.info("Session %s created for '%s'", session_id, pptx.filename)
    return SessionCreateResponse(session_id=session_id, status="queued")


@router.get("", response_model=list[SessionListItem])
async def list_sessions(user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    """Your decks, most recent first (signed out: decks uploaded without an account)."""
    owner = Session.user_id == user.id if user else Session.user_id.is_(None)
    result = await db.execute(select(Session).where(owner).order_by(Session.created_at.desc()))
    return [
        SessionListItem(
            session_id=s.id,
            original_filename=s.original_filename,
            status=s.status,
            slide_count=s.slide_count,
            created_at=s.created_at,
        )
        for s in result.scalars()
    ]


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Poll session status and per-slide progress."""
    session = await get_session_or_404(db, session_id, user)

    slides_progress = None
    if session.slide_count:
        slides = await get_slides(db, session_id)
        statuses = [s.status for s in slides]
        slides_progress = SlidesProgress(
            rendered=sum(st in ("rendered", "scripted", "synthesized") for st in statuses),
            scripted=sum(st in ("scripted", "synthesized") for st in statuses),
            synthesized=sum(st == "synthesized" for st in statuses),
            total=session.slide_count,
        )

    return SessionStatusResponse(
        session_id=session.id,
        status=session.status,
        slide_count=session.slide_count,
        slides_progress=slides_progress,
        error_detail=session.error_detail,
        warnings=session.warnings or [],
        video_ready=session.status == "complete" and bool(session.video_storage_path),
        voice_cloning_used=session.voice_cloning_used,
        original_filename=session.original_filename,
        narrator_voice=session.narrator_voice,
        insights=session.insights,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/{session_id}/retry", response_model=SessionCreateResponse, status_code=202)
async def retry_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Re-run the Ideal Presentation Agent for a failed (or completed) session."""
    session = await get_session_or_404(db, session_id, user)
    if session.status in SESSION_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail=f"Session is still running ({session.status})")
    session.status = "queued"
    session.error_detail = None
    await db.commit()
    tasks.spawn(run_ideal_presentation_pipeline(session_id), name=f"ideal-retry-{session_id}")
    return SessionCreateResponse(session_id=session_id, status="queued")


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Delete a session, its practice runs and all stored files."""
    session = await get_session_or_404(db, session_id, user)
    if session.status in SESSION_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="Wait for the pipeline to finish before deleting")
    await db.delete(session)
    await db.commit()
    storage_service.delete_session(str(session_id))


@router.get("/{session_id}/scripts", response_model=SlideScriptsResponse)
async def get_session_scripts(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Per-slide narration scripts, with each slide's start time in the ideal video."""
    await get_session_or_404(db, session_id, user)
    slides = await get_slides(db, session_id)

    out, cursor = [], 0.0
    for s in slides:
        duration = s.audio_duration_sec + SLIDE_GAP_SEC if s.audio_duration_sec else None
        out.append(SlideScript(
            slide_index=s.slide_index,
            script_text=s.script_text,
            word_count=s.script_word_count,
            script_source=s.script_source,
            audio_source=s.audio_source,
            start_sec=round(cursor, 3) if duration else None,
            duration_sec=round(duration, 3) if duration else None,
            status=s.status,
        ))
        cursor += duration or 0.0
    return SlideScriptsResponse(slides=out)


@router.get("/{session_id}/video")
async def get_session_video(session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """The final narrated ideal-presentation video (MP4)."""
    session = await get_session_or_404(db, session_id, user)
    if session.status != "complete" or not session.video_storage_path:
        raise HTTPException(status_code=409, detail=f"Video not ready (status: {session.status})")

    video_path = storage_service.get_absolute_path(session.video_storage_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"{session.original_filename.rsplit('.', 1)[0]}_ideal.mp4",
        content_disposition_type="inline",
    )


async def _slide_or_404(db: AsyncSession, session_id: uuid.UUID, slide_index: int) -> Slide:
    slide = (await db.execute(
        select(Slide).where(Slide.session_id == session_id, Slide.slide_index == slide_index)
    )).scalar_one_or_none()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    return slide


@router.get("/{session_id}/slides/{slide_index}/image")
async def get_slide_image(session_id: uuid.UUID, slide_index: int, db: AsyncSession = Depends(get_db)):
    """A slide's rendered PNG."""
    slide = await _slide_or_404(db, session_id, slide_index)
    path = storage_service.get_absolute_path(slide.png_storage_path) if slide.png_storage_path else None
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Slide image not available")
    return FileResponse(path=str(path), media_type="image/png")


@router.get("/{session_id}/slides/{slide_index}/audio")
async def get_slide_audio(session_id: uuid.UUID, slide_index: int, db: AsyncSession = Depends(get_db)):
    """A slide's ideal narration audio (WAV) — handy for per-slide practice."""
    slide = await _slide_or_404(db, session_id, slide_index)
    path = storage_service.get_absolute_path(slide.audio_storage_path) if slide.audio_storage_path else None
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Slide audio not available")
    return FileResponse(path=str(path), media_type="audio/wav")
