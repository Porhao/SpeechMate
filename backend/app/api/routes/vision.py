from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.base import get_db
from app.models.user import User
from app.models.session import VisionAnalysis as VisionAnalysisModel, SpeechAnalysis as SpeechAnalysisModel
from app.schemas.session import VisionAnalysisResponse, AnalyzeRequest
from app.middleware.auth import get_current_user
from app.services import storage
from app.ai.vision.eye_contact import eye_contact_detector
from app.ai.vision.emotion import emotion_detector
from app.ai.vision.posture import posture_analyzer
from app.ai.speech.confidence import estimate_confidence
import uuid

router = APIRouter(prefix="/vision", tags=["Vision Analysis"])


@router.post("/upload")
async def upload_video(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    saved_path = await storage.save_upload(session_id, file)
    return {"file_url": str(saved_path), "session_id": session_id}


@router.post("/analyze", response_model=VisionAnalysisResponse)
async def analyze_vision(
    body: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media_path = storage.get_media_path(body.session_id)
    video_path = str(media_path) if media_path else ""

    # Run vision AI services
    eye = await eye_contact_detector.analyze_video(video_path)
    emotion = await emotion_detector.analyze_video(video_path)
    posture = await posture_analyzer.analyze_video(video_path)

    # Pull this session's speech analysis (if it already ran) for real
    # speaking-rate/fluency figures to feed the confidence estimate;
    # fall back to neutral defaults if speech hasn't been analyzed yet.
    # SpeechAnalysis has no timestamp column to order by recency; a session
    # is expected to be analyzed once, but be defensive and just take one
    # row rather than crash if /speech/analyze was ever called more than once.
    result = await db.execute(
        select(SpeechAnalysisModel).where(SpeechAnalysisModel.session_id == body.session_id).limit(1)
    )
    speech_row = result.scalar_one_or_none()
    speaking_rate = speech_row.speaking_rate if speech_row else 130.0
    fluency_score = speech_row.fluency_score if speech_row else 75.0
    pause_frequency = 5  # not persisted on SpeechAnalysis; use a neutral estimate

    confidence = estimate_confidence(
        speaking_rate=speaking_rate,
        pause_frequency=pause_frequency,
        fluency_score=fluency_score,
        emotion_confidence=emotion.confidence_level,
        facial_tension=emotion.facial_tension,
        posture_score=posture.posture_score,
        body_stability=posture.body_stability,
    )

    # Persist to database
    analysis = VisionAnalysisModel(
        id=str(uuid.uuid4()),
        session_id=body.session_id,
        eye_contact_score=eye.eye_contact_score,
        confidence_score=confidence.confidence_score,
        posture_score=posture.posture_score,
        emotion_label=emotion.dominant_emotion,
    )
    db.add(analysis)
    await db.commit()

    return VisionAnalysisResponse(
        eye_contact=eye.eye_contact_score,
        confidence=confidence.confidence_score,
        posture=posture.posture_score,
    )
