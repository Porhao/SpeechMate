"""
End-to-End AI Analysis Pipeline
Orchestrates all AI services for a complete communication assessment.

Flow:
Audio + Video → ASR → Speech Analysis → Vision Analysis
             → Confidence Estimation → Communication Scoring
             → Recommendation Engine → Structured Feedback
"""
from dataclasses import dataclass, field
from pathlib import Path

from .speech.asr import asr_service, ASRResult
from .speech.fluency import analyze_fluency, FluencyResult
from .speech.stuttering import stuttering_detector, StutteringResult
from .speech.pronunciation import pronunciation_assessor, PronunciationResult
from .speech.fillers import detect_fillers, FillerResult
from .speech.confidence import estimate_confidence, ConfidenceResult
from .speech.scoring import compute_communication_score, CommunicationScore
from .speech.malaysian import detect_language_and_accent, adjust_pronunciation_score_for_accent
from .vision.eye_contact import eye_contact_detector, EyeContactResult
from .vision.emotion import emotion_detector, EmotionResult
from .vision.posture import posture_analyzer, PostureResult
from .recommendation.engine import generate_recommendations, RecommendationResult


@dataclass
class FullAnalysisResult:
    session_id: str
    asr: ASRResult
    fluency: FluencyResult
    stuttering: StutteringResult
    pronunciation: PronunciationResult
    fillers: FillerResult
    eye_contact: EyeContactResult
    emotion: EmotionResult
    posture: PostureResult
    confidence: ConfidenceResult
    communication_score: CommunicationScore
    recommendations: RecommendationResult
    language_detection: dict = field(default_factory=dict)


async def run_full_analysis(
    session_id: str,
    audio_path: str | Path | None = None,
    video_path: str | Path | None = None,
    user_goal: str = "",
    session_history_count: int = 0,
) -> FullAnalysisResult:
    """
    Run the complete multimodal AI analysis pipeline.
    In production: audio_path and video_path point to MinIO-stored files.
    In dev (no files): all services return stub data.
    """

    # Step 1: ASR — transcribe audio
    asr = await asr_service.transcribe(audio_path or "")

    # Step 2: Malaysian language detection (adjust subsequent models)
    lang = detect_language_and_accent(asr.transcript)

    # Step 3: Speech analysis (all run on transcript + ASR result)
    fluency = analyze_fluency(asr)
    stuttering = await stuttering_detector.detect(str(audio_path or ""), asr.transcript, asr.word_timestamps)
    pronunciation_raw = await pronunciation_assessor.assess(
        str(audio_path or ""), asr.transcript, lang.primary_language
    )
    fillers = detect_fillers(asr.transcript, asr.duration_seconds)

    # Step 4: Adjust pronunciation for Malaysian accent
    adjusted_pron_score = adjust_pronunciation_score_for_accent(
        pronunciation_raw.score, lang
    )
    pronunciation_raw.score = adjusted_pron_score

    # Step 5: Vision analysis (all run on video frames)
    eye_contact = await eye_contact_detector.analyze_video(str(video_path or ""))
    emotion = await emotion_detector.analyze_video(str(video_path or ""))
    posture = await posture_analyzer.analyze_video(str(video_path or ""))

    # Step 6: Confidence estimation (cross-modal)
    confidence = estimate_confidence(
        speaking_rate=fluency.speaking_rate,
        pause_frequency=fluency.pause_frequency,
        fluency_score=fluency.fluency_score,
        emotion_confidence=emotion.confidence_level,
        facial_tension=emotion.facial_tension,
        posture_score=posture.posture_score,
        body_stability=posture.body_stability,
    )

    # Step 7: Overall communication score
    comm_score = compute_communication_score(
        fluency=fluency.fluency_score,
        pronunciation=pronunciation_raw.score,
        confidence=confidence.confidence_score,
        eye_contact=eye_contact.eye_contact_score,
        posture=posture.posture_score,
    )

    # Step 8: Personalized recommendations
    recommendations = generate_recommendations(
        fluency_score=fluency.fluency_score,
        pronunciation_score=pronunciation_raw.score,
        eye_contact_score=eye_contact.eye_contact_score,
        confidence_score=confidence.confidence_score,
        posture_score=posture.posture_score,
        stuttering_score=stuttering.stuttering_score,
        filler_count=fillers.total_fillers,
        user_goal=user_goal,
        session_history_count=session_history_count,
    )

    return FullAnalysisResult(
        session_id=session_id,
        asr=asr,
        fluency=fluency,
        stuttering=stuttering,
        pronunciation=pronunciation_raw,
        fillers=fillers,
        eye_contact=eye_contact,
        emotion=emotion,
        posture=posture,
        confidence=confidence,
        communication_score=comm_score,
        recommendations=recommendations,
        language_detection={
            "primary_language": lang.primary_language,
            "is_code_switching": lang.is_code_switching,
            "accent_type": lang.accent_type,
            "english_ratio": lang.english_ratio,
            "malay_ratio": lang.malay_ratio,
        },
    )
