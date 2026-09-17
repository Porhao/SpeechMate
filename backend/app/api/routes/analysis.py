"""
Full Analysis Endpoint — runs the complete AI pipeline for a session.
Called after a practice session ends.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database.base import get_db
from app.models.user import User
from app.models.session import (
    PracticeSession, SpeechAnalysis, VisionAnalysis,
    AIFeedback, ProgressHistory,
)
from app.middleware.auth import get_current_user
from app.services import storage
from app.ai.pipeline import run_full_analysis
import uuid

router = APIRouter(prefix="/analysis", tags=["Full Analysis"])


class FullAnalysisRequest(BaseModel):
    session_id: str


@router.post("/run")
async def run_analysis(
    body: FullAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get session history count for recommendation personalisation
    result = await db.execute(
        select(PracticeSession).where(PracticeSession.user_id == current_user.id)
    )
    history_count = len(result.scalars().all())

    # Resolve the session's saved recording (same file serves both audio and
    # video analysis — see app.services.storage)
    media_path = storage.get_media_path(body.session_id)

    # Run full AI pipeline
    analysis = await run_full_analysis(
        session_id=body.session_id,
        audio_path=media_path,
        video_path=media_path,
        user_goal=current_user.role,  # Will be replaced with profile.communication_goal
        session_history_count=history_count,
    )

    # Persist speech analysis
    speech_row = SpeechAnalysis(
        id=str(uuid.uuid4()),
        session_id=body.session_id,
        fluency_score=analysis.fluency.fluency_score,
        pronunciation_score=analysis.pronunciation.score,
        speaking_rate=analysis.fluency.speaking_rate,
        filler_word_count=analysis.fillers.total_fillers,
        stuttering_score=analysis.stuttering.stuttering_score,
    )
    db.add(speech_row)

    # Persist vision analysis
    vision_row = VisionAnalysis(
        id=str(uuid.uuid4()),
        session_id=body.session_id,
        eye_contact_score=analysis.eye_contact.eye_contact_score,
        confidence_score=analysis.confidence.confidence_score,
        posture_score=analysis.posture.posture_score,
        emotion_label=analysis.emotion.dominant_emotion,
    )
    db.add(vision_row)

    # Persist AI feedback
    feedback_row = AIFeedback(
        id=str(uuid.uuid4()),
        session_id=body.session_id,
        summary=(
            f"Overall score: {analysis.communication_score.overall_score}% "
            f"({analysis.communication_score.grade}). "
            f"Strengths: {', '.join(analysis.communication_score.strengths) or 'Keep practicing!'}. "
            f"Focus areas: {', '.join(analysis.communication_score.improvement_areas) or 'None identified'}."
        ),
        recommendations=[r.title for r in analysis.recommendations.recommendations],
    )
    db.add(feedback_row)

    # Persist progress history (one row per metric)
    metrics = {
        "fluency_score": analysis.fluency.fluency_score,
        "pronunciation_score": analysis.pronunciation.score,
        "eye_contact_score": analysis.eye_contact.eye_contact_score,
        "confidence_score": analysis.confidence.confidence_score,
        "posture_score": analysis.posture.posture_score,
        "overall_score": analysis.communication_score.overall_score,
    }
    for metric_name, value in metrics.items():
        db.add(ProgressHistory(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            metric_name=metric_name,
            metric_value=value,
        ))

    await db.commit()

    # Return full structured result
    return {
        "session_id": body.session_id,
        "transcript": analysis.asr.transcript,
        "language": analysis.language_detection,
        "speech": {
            "fluency_score": analysis.fluency.fluency_score,
            "speaking_rate": analysis.fluency.speaking_rate,
            "pronunciation_score": analysis.pronunciation.score,
            "stuttering_score": analysis.stuttering.stuttering_score,
            "stuttering_severity": analysis.stuttering.severity,
            "filler_count": analysis.fillers.total_fillers,
            "filler_per_minute": analysis.fillers.fillers_per_minute,
            "top_filler": analysis.fillers.top_filler,
            "pause_frequency": analysis.fluency.pause_frequency,
            "fluency_grade": analysis.fluency.grade,
        },
        "vision": {
            "eye_contact_score": analysis.eye_contact.eye_contact_score,
            "posture_score": analysis.posture.posture_score,
            "dominant_emotion": analysis.emotion.dominant_emotion,
            "confidence_score": analysis.confidence.confidence_score,
            "confidence_label": analysis.confidence.label,
        },
        "communication_score": {
            "overall_score": analysis.communication_score.overall_score,
            "grade": analysis.communication_score.grade,
            "strengths": analysis.communication_score.strengths,
            "improvement_areas": analysis.communication_score.improvement_areas,
        },
        "recommendations": {
            "weekly_focus": analysis.recommendations.weekly_focus,
            "daily_target_minutes": analysis.recommendations.daily_target_minutes,
            "tips": analysis.recommendations.tips,
            "progress_forecast": analysis.recommendations.progress_forecast,
            "exercises": [
                {
                    "title": r.title,
                    "description": r.description,
                    "practice_type": r.practice_type,
                    "daily_minutes": r.daily_minutes,
                    "priority": r.priority,
                    "metric_target": r.metric_target,
                }
                for r in analysis.recommendations.recommendations
            ],
        },
    }
