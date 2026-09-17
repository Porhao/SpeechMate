from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import get_db
from app.models.user import User
from app.models.session import SpeechAnalysis as SpeechAnalysisModel
from app.schemas.session import SpeechAnalysisResponse, AnalyzeRequest
from app.middleware.auth import get_current_user
from app.services import storage
from app.ai.speech.asr import asr_service
from app.ai.speech.fluency import analyze_fluency
from app.ai.speech.stuttering import stuttering_detector
from app.ai.speech.pronunciation import pronunciation_assessor
from app.ai.speech.fillers import detect_fillers
from app.ai.speech.malaysian import detect_language_and_accent, adjust_pronunciation_score_for_accent
import uuid

router = APIRouter(prefix="/speech", tags=["Speech Analysis"])


@router.post("/upload")
async def upload_audio(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    saved_path = await storage.save_upload(session_id, file)
    return {"file_url": str(saved_path), "session_id": session_id}


@router.post("/analyze", response_model=SpeechAnalysisResponse)
async def analyze_speech(
    body: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    media_path = storage.get_media_path(body.session_id)
    audio_path = str(media_path) if media_path else ""

    # Run ASR pipeline (real model if a recording was uploaded, stub otherwise)
    asr = await asr_service.transcribe(audio_path)

    # Detect language (English / BM / code-switching)
    lang = detect_language_and_accent(asr.transcript)

    # Run all speech AI services
    fluency = analyze_fluency(asr)
    stuttering = await stuttering_detector.detect(audio_path, asr.transcript, asr.word_timestamps)
    pronunciation = await pronunciation_assessor.assess(audio_path, asr.transcript, lang.primary_language)
    fillers = detect_fillers(asr.transcript, asr.duration_seconds)

    # Adjust pronunciation for Malaysian accent
    pronunciation.score = adjust_pronunciation_score_for_accent(pronunciation.score, lang)

    # Persist to database
    analysis = SpeechAnalysisModel(
        id=str(uuid.uuid4()),
        session_id=body.session_id,
        fluency_score=fluency.fluency_score,
        pronunciation_score=pronunciation.score,
        speaking_rate=fluency.speaking_rate,
        filler_word_count=fillers.total_fillers,
        stuttering_score=stuttering.stuttering_score,
    )
    db.add(analysis)
    await db.commit()

    return SpeechAnalysisResponse(
        fluency_score=fluency.fluency_score,
        pronunciation_score=pronunciation.score,
        stuttering_score=stuttering.stuttering_score,
        speaking_rate=fluency.speaking_rate,
        filler_word_count=fillers.total_fillers,
    )
