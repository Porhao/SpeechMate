"""Live practice sessions (camera + mic with the AI partner): start/end, upload the
recording and run the multimodal analysis."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_owned, require_cloud_consent
from app.database import get_db
from app.models.live_session import LIVE_IN_PROGRESS_STATUSES, NEVER_USED, LiveSession, results_link
from app.models.notification import Notification
from app.models.session import Session as Deck
from app.models.user import User
from app.schemas.live import (
    InterviewSetup,
    LiveEndRequest,
    LiveSessionResponse,
    LiveStartRequest,
    PracticePlan,
)
from app.services import decks, documents, plans, tasks
from app.services.learner import first_name, learner_brief
from app.services.live.pipeline import run_live_analysis
from app.limits import MB, rate_limit, read_limited, save_limited
from app.services.storage import live_folder, storage_service

router = APIRouter(tags=["live sessions"])

AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".oga", ".flac", ".aac", ".mp4", ".mov"}


def audio_extension(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext or '?'}'. Use one of: {', '.join(sorted(AUDIO_EXTENSIONS))}",
        )
    return ext


def _to_response(s: LiveSession) -> LiveSessionResponse:
    return LiveSessionResponse(
        id=s.id,
        session_type=s.session_type,
        duration_sec=s.duration_sec,
        status=s.status,
        has_recording=bool(s.recording_storage_path),
        error_detail=s.error_detail,
        warnings=s.warnings or [],
        analysis=s.analysis,
        context=s.context,
        turns=s.turns,
        created_at=s.created_at,
    )


MAX_RESUME_BYTES = 5 * MB
MAX_RECORDING_BYTES = 500 * MB  # ~25 min of 720p webm; recordings stream to disk, never into memory


@router.post("/interview/resume", dependencies=[Depends(rate_limit("resume", 10))])
async def read_resume(
    file: UploadFile = File(..., description="Resume as PDF, DOCX or TXT"),
    user: User = Depends(get_current_user),
):
    """Extract the resume's text so the user can check it before it's used for the interview.
    Nothing is stored here; the text is saved only with the interview session it's used in."""
    data = await read_limited(file, MAX_RESUME_BYTES, "The resume")
    try:
        text = documents.extract_resume_text(data, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"text": text}


@router.post("/interview/plan", response_model=PracticePlan, dependencies=[Depends(rate_limit("plan", 6))])
async def interview_plan(body: InterviewSetup, user: User = Depends(require_cloud_consent)):
    """Curate the mock-interview questions from the candidate's setup (and resume) for preview."""
    return await plans.build_interview_plan(body.model_dump(exclude_none=True), first_name(user), learner_brief(user))


async def _deck_context(db: AsyncSession, user: User, deck_id: uuid.UUID, mode: str, use_script: bool) -> dict:
    deck = await get_owned(db, Deck, deck_id, user, "Deck")
    if not deck.insights:
        raise HTTPException(status_code=409, detail="This deck hasn't been analysed yet: wait for its insights first")
    base = {"deck_id": str(deck.id), "deck_title": decks.title(deck), "deck_summary": deck.insights.get("summary", ""),
            "audience": deck.requirement_prompt}
    if mode == "talk":
        # What each slide is about, to check the talk against; with the script, what it planned too
        slides = await decks.slides(db, deck)
        if use_script:
            if not deck.script:
                raise HTTPException(status_code=409, detail="Write a script for this deck first")
            plan = {p["slide_index"]: p for p in deck.script["slides"]}
            for s in slides:
                if p := plan.get(s["index"]):
                    s.update(script=p["text"], budget_sec=p["seconds"])
        return {**base, "kind": "talk", "slides": slides, **({"script": True} if use_script else {})}
    return {**base, "kind": "qa", "plan": await decks.qa_plan(deck, learner_brief(user))}


@router.post("/live", response_model=LiveSessionResponse, status_code=201)
async def start_live_session(
    body: LiveStartRequest, user: User = Depends(require_cloud_consent), db: AsyncSession = Depends(get_db)
):
    """Start a session. Interview needs `interview` (the setup); Presentation needs `deck_id`.
    Both get a curated question plan that the AI partner follows."""
    context: dict | None = None
    if body.session_type == "Interview":
        if not body.interview:
            raise HTTPException(status_code=422, detail="Tell us about the interview first (position, background…)")
        setup = body.interview.model_dump(exclude_none=True)
        resume_text = setup.pop("resume_text", None)
        plan = body.plan.model_dump() if body.plan else await plans.build_interview_plan(
            {**setup, **({"resume_text": resume_text} if resume_text else {})}, first_name(user), learner_brief(user))
        context = {"setup": setup, "resume_text": resume_text, "plan": plan}
    elif body.session_type == "Presentation":
        if not body.deck_id:
            raise HTTPException(status_code=422, detail="Choose the deck to rehearse the Q&A for")
        context = await _deck_context(db, user, body.deck_id, body.presentation_mode, body.use_script)
    elif body.topic:
        context = {"topic": body.topic}
    if context and context.get("plan"):
        context["progress"] = {"asked": 0, "followups": 0}
    s = LiveSession(user_id=user.id, session_type=body.session_type, status="active", context=context)
    db.add(s)
    await db.commit()
    return _to_response(s)


def _summary(s: LiveSession) -> LiveSessionResponse:
    """A list row: what the history, home (tasks) and deck pages show. The turns, question plan and
    résumé text stay out of it (GET /live/{id} has everything)."""
    a, c = s.analysis or {}, s.context or {}
    r = _to_response(s)
    r.turns = None
    r.context = {k: c[k] for k in ("kind", "topic", "deck_id", "deck_title") if k in c} | (
        {"setup": {"position": c["setup"].get("position")}} if isinstance(c.get("setup"), dict) else {})
    r.analysis = {
        "communication_score": {"overall_score": (a.get("communication_score") or {}).get("overall_score")},
        "recommendations": {"exercises": (a.get("recommendations") or {}).get("exercises") or []},  # the 3 drills: Home's tasks
        "pillars": a.get("pillars"),
    } if a else None
    return r


@router.get("/live", response_model=list[LiveSessionResponse])
async def list_live_sessions(deck_id: uuid.UUID | None = None, user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    """The user's attempts as summaries, most recent first; `deck_id` keeps one deck's attempts."""
    q = select(LiveSession).where(LiveSession.user_id == user.id, ~NEVER_USED)
    if deck_id:
        q = q.where(LiveSession.context["deck_id"].as_string() == str(deck_id))
    result = await db.execute(q.order_by(LiveSession.created_at.desc()))
    return [_summary(s) for s in result.scalars()]


@router.get("/live/{live_id}", response_model=LiveSessionResponse)
async def get_live_session(
    live_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Poll here after requesting analysis; `analysis` appears once status is `complete`."""
    return _to_response(await get_owned(db, LiveSession, live_id, user, "Live session"))


@router.post("/live/{live_id}/end", response_model=LiveSessionResponse)
async def end_live_session(
    live_id: uuid.UUID,
    body: LiveEndRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await get_owned(db, LiveSession, live_id, user, "Live session")
    s.duration_sec = body.duration_sec
    if body.turns:
        s.turns = [t.model_dump() for t in body.turns]
    if body.client_metrics:
        s.client_metrics = body.client_metrics.model_dump()
    await db.commit()
    return _to_response(s)


@router.post("/live/{live_id}/recording", response_model=LiveSessionResponse)
async def upload_recording(
    live_id: uuid.UUID,
    file: UploadFile = File(..., description="The session recording (webm/mp4 with audio + video, or audio only)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await get_owned(db, LiveSession, live_id, user, "Live session")
    if s.status in LIVE_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="This session is being analysed")
    ext = audio_extension(file.filename)
    path = storage_service.path(live_folder(live_id), f"recording{ext}")
    await save_limited(file, path, MAX_RECORDING_BYTES, "The recording")
    s.recording_storage_path = storage_service.relative(path
    )
    await db.commit()
    return _to_response(s)


@router.post("/live/{live_id}/analyze", response_model=LiveSessionResponse, status_code=202)
async def analyze_live_session(
    live_id: uuid.UUID, user: User = Depends(require_cloud_consent), db: AsyncSession = Depends(get_db)
):
    """Start the multimodal analysis in the background; poll GET /live/{id}."""
    s = await get_owned(db, LiveSession, live_id, user, "Live session")
    if not s.recording_storage_path:
        raise HTTPException(status_code=409, detail="Upload the recording before analysing")
    if s.status in LIVE_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="Analysis is already running")
    s.status, s.error_detail, s.warnings, s.analysis = "analyzing", None, None, None
    await db.commit()
    tasks.spawn(run_live_analysis(live_id), name=f"live-{live_id}")
    return _to_response(s)


@router.delete("/live/{live_id}", status_code=204)
async def delete_live_session(
    live_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    s = await get_owned(db, LiveSession, live_id, user, "Live session")
    if s.status in LIVE_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="Wait for the analysis to finish before deleting")
    await db.delete(s)
    # Its notifications ("results are ready", "analysis failed") would open a page that's gone
    await db.execute(delete(Notification).where(Notification.user_id == user.id, Notification.link == results_link(live_id)))
    await db.commit()
    storage_service.delete_folder(live_folder(live_id))

