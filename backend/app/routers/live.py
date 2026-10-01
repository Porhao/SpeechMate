"""Live practice sessions (camera + mic with the AI partner): start/end, upload the
recording, run the multimodal analysis, and read progress history and reports."""

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.live_session import LIVE_IN_PROGRESS_STATUSES, LiveSession, ProgressRecord, Report
from app.models.session import Session as Deck
from app.models.user import User
from app.routers.sessions import audio_extension
from app.schemas.live import (
    InterviewSetup,
    LiveEndRequest,
    LiveSessionResponse,
    LiveStartRequest,
    PracticePlan,
    ProgressRecordOut,
    ReportOut,
)
from app.services import practice_plans, tasks
from app.services.live.pipeline import run_live_analysis
from app.services.storage import storage_service

router = APIRouter(tags=["live sessions"])

LIVE_STORAGE_PREFIX = "live"


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


async def _own_session(db: AsyncSession, user: User, live_id: uuid.UUID) -> LiveSession:
    s = (await db.execute(
        select(LiveSession).where(LiveSession.id == live_id, LiveSession.user_id == user.id)
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Live session not found")
    return s


MAX_RESUME_BYTES = 5 * 1024 * 1024


def _first_name(user: User) -> str | None:
    return (user.full_name or "").split(" ")[0] or None


@router.post("/interview/resume")
async def read_resume(
    file: UploadFile = File(..., description="Resume as PDF, DOCX or TXT"),
    user: User = Depends(get_current_user),
):
    """Extract the resume's text so the user can check it before it's used for the interview.
    Nothing is stored here; the text is saved only with the interview session it's used in."""
    data = await file.read()
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="Resume must be under 5 MB")
    try:
        text = practice_plans.extract_resume_text(data, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"text": text, "chars": len(text)}


@router.post("/interview/plan", response_model=PracticePlan)
async def interview_plan(body: InterviewSetup, user: User = Depends(get_current_user)):
    """Curate the mock-interview questions from the candidate's setup (and resume) for preview."""
    return await practice_plans.build_interview_plan(body.model_dump(exclude_none=True), _first_name(user))


async def _deck_context(db: AsyncSession, user: User, deck_id: uuid.UUID) -> dict:
    deck = await db.get(Deck, deck_id)
    if not deck or (deck.user_id is not None and deck.user_id != user.id):
        raise HTTPException(status_code=404, detail="Deck not found")
    if not deck.insights:
        raise HTTPException(status_code=409, detail="This deck hasn't been analysed yet: wait for its insights first")
    title = deck.original_filename.rsplit(".", 1)[0]
    plan = await practice_plans.build_qa_plan(title, deck.insights, deck.requirement_prompt)
    return {"deck_id": str(deck.id), "deck_title": title, "deck_summary": deck.insights.get("summary", ""),
            "audience": deck.requirement_prompt, "plan": plan}


@router.post("/live", response_model=LiveSessionResponse, status_code=201)
async def start_live_session(
    body: LiveStartRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Start a session. Interview needs `interview` (the setup); Presentation needs `deck_id`.
    Both get a curated question plan that the AI partner follows."""
    context: dict | None = None
    if body.session_type == "Interview":
        if not body.interview:
            raise HTTPException(status_code=422, detail="Tell us about the interview first (position, background…)")
        setup = body.interview.model_dump(exclude_none=True)
        resume_text = setup.pop("resume_text", None)
        plan = body.plan.model_dump() if body.plan else await practice_plans.build_interview_plan(
            {**setup, **({"resume_text": resume_text} if resume_text else {})}, _first_name(user))
        context = {"setup": setup, "resume_text": resume_text, "plan": plan}
    elif body.session_type == "Presentation":
        if not body.deck_id:
            raise HTTPException(status_code=422, detail="Choose the deck to rehearse the Q&A for")
        context = await _deck_context(db, user, body.deck_id)
    elif body.topic:
        context = {"topic": body.topic}
    if context and context.get("plan"):
        context["progress"] = {"asked": 0, "followups": 0}
    s = LiveSession(user_id=user.id, session_type=body.session_type, status="active", context=context)
    db.add(s)
    await db.commit()
    return _to_response(s)


@router.get("/live", response_model=list[LiveSessionResponse])
async def list_live_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """The user's live sessions, most recent first."""
    result = await db.execute(
        select(LiveSession).where(LiveSession.user_id == user.id).order_by(LiveSession.created_at.desc())
    )
    return [_to_response(s) for s in result.scalars()]


@router.get("/live/{live_id}", response_model=LiveSessionResponse)
async def get_live_session(
    live_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Poll here after requesting analysis; `analysis` appears once status is `complete`."""
    return _to_response(await _own_session(db, user, live_id))


@router.post("/live/{live_id}/end", response_model=LiveSessionResponse)
async def end_live_session(
    live_id: uuid.UUID,
    body: LiveEndRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await _own_session(db, user, live_id)
    s.duration_sec = body.duration_sec
    if body.turns:
        s.turns = [t.model_dump() for t in body.turns]
    if body.client_metrics:
        s.client_metrics = body.client_metrics
    await db.commit()
    return _to_response(s)


@router.post("/live/{live_id}/recording", response_model=LiveSessionResponse)
async def upload_recording(
    live_id: uuid.UUID,
    file: UploadFile = File(..., description="The session recording (webm/mp4 with audio + video, or audio only)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await _own_session(db, user, live_id)
    if s.status in LIVE_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="This session is being analysed")
    ext = audio_extension(file.filename)
    s.recording_storage_path = await storage_service.save_upload(
        f"{LIVE_STORAGE_PREFIX}/{live_id}", f"recording{ext}", await file.read()
    )
    await db.commit()
    return _to_response(s)


@router.post("/live/{live_id}/analyze", response_model=LiveSessionResponse, status_code=202)
async def analyze_live_session(
    live_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Start the multimodal analysis in the background; poll GET /live/{id}."""
    s = await _own_session(db, user, live_id)
    if not s.recording_storage_path:
        raise HTTPException(status_code=409, detail="Upload the recording before analysing")
    if s.status in LIVE_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="Analysis is already running")
    # Re-analysis replaces this session's earlier progress points
    await db.execute(delete(ProgressRecord).where(ProgressRecord.live_session_id == live_id))
    s.status, s.error_detail, s.warnings, s.analysis = "analyzing", None, None, None
    await db.commit()
    tasks.spawn(run_live_analysis(live_id), name=f"live-{live_id}")
    return _to_response(s)


@router.delete("/live/{live_id}", status_code=204)
async def delete_live_session(
    live_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    s = await _own_session(db, user, live_id)
    if s.status in LIVE_IN_PROGRESS_STATUSES:
        raise HTTPException(status_code=409, detail="Wait for the analysis to finish before deleting")
    await db.delete(s)
    await db.commit()
    storage_service.delete_session(f"{LIVE_STORAGE_PREFIX}/{live_id}")


@router.get("/progress", response_model=list[ProgressRecordOut])
async def get_progress(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Every metric from every analysed live session, oldest first (for charts)."""
    result = await db.execute(
        select(ProgressRecord).where(ProgressRecord.user_id == user.id).order_by(ProgressRecord.recorded_at)
    )
    return [
        ProgressRecordOut(
            id=r.id, live_session_id=r.live_session_id, metric_name=r.metric_name,
            metric_value=r.metric_value, recorded_at=r.recorded_at,
        )
        for r in result.scalars()
    ]


# ── Reports ─────────────────────────────────────────────────────────────────

def _report_out(r: Report) -> ReportOut:
    return ReportOut(
        id=r.id, report_type=r.report_type, report_url=f"/api/reports/{r.id}",
        content=r.content, created_at=r.created_at,
    )


@router.post("/reports/generate", response_model=ReportOut, status_code=201)
async def generate_report(
    report_type: str = "summary", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Snapshot the user's progress: per-metric averages, first/latest/best values and session counts."""
    sessions = list((await db.execute(
        select(LiveSession).where(LiveSession.user_id == user.id).order_by(LiveSession.created_at)
    )).scalars())
    records = list((await db.execute(
        select(ProgressRecord).where(ProgressRecord.user_id == user.id).order_by(ProgressRecord.recorded_at)
    )).scalars())

    series: dict[str, list[float]] = defaultdict(list)
    for r in records:
        series[r.metric_name].append(r.metric_value)
    metrics = {
        name: {
            "sessions": len(vals),
            "average": round(sum(vals) / len(vals), 1),
            "first": vals[0],
            "latest": vals[-1],
            "best": max(vals),
            "change": round(vals[-1] - vals[0], 1),
        }
        for name, vals in series.items()
    }
    by_type: dict[str, int] = defaultdict(int)
    for s in sessions:
        by_type[s.session_type] += 1
    analysed = [s for s in sessions if s.status == "complete" and s.analysis]
    latest = analysed[-1].analysis if analysed else None

    content = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": {"full_name": user.full_name, "communication_goal": user.communication_goal},
        "totals": {
            "sessions": len(sessions),
            "analysed_sessions": len(analysed),
            "practice_minutes": round(sum(s.duration_sec for s in sessions) / 60, 1),
            "by_type": dict(by_type),
        },
        "metrics": metrics,
        "latest_recommendations": (latest or {}).get("recommendations"),
        "latest_strengths": ((latest or {}).get("communication_score") or {}).get("strengths", []),
        "latest_improvement_areas": ((latest or {}).get("communication_score") or {}).get("improvement_areas", []),
    }
    report = Report(user_id=user.id, report_type=report_type, content=content)
    db.add(report)
    await db.commit()
    return _report_out(report)


@router.get("/reports", response_model=list[ReportOut])
async def list_reports(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.user_id == user.id).order_by(Report.created_at.desc()))
    return [_report_out(r) for r in result.scalars()]


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    report = (await db.execute(
        select(Report).where(Report.id == report_id, Report.user_id == user.id)
    )).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_out(report)
