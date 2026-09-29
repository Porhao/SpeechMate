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
from app.models.user import User
from app.routers.sessions import audio_extension
from app.schemas.live import (
    LiveEndRequest,
    LiveSessionResponse,
    LiveStartRequest,
    ProgressRecordOut,
    ReportOut,
)
from app.services import tasks
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
        created_at=s.created_at,
    )


async def _own_session(db: AsyncSession, user: User, live_id: uuid.UUID) -> LiveSession:
    s = (await db.execute(
        select(LiveSession).where(LiveSession.id == live_id, LiveSession.user_id == user.id)
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Live session not found")
    return s


@router.post("/live", response_model=LiveSessionResponse, status_code=201)
async def start_live_session(
    body: LiveStartRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    s = LiveSession(user_id=user.id, session_type=body.session_type, status="active")
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
