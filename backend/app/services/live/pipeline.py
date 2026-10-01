"""Live-session analysis pipeline (background job).

    recording → 16 kHz WAV → ASR (+ code-switch routing) → language detection
      → fluency / fillers / stuttering / pronunciation
      → eye contact / posture / emotion (video frames)
      → confidence → communication score → recommendations
      → progress records

    status: analyzing → complete | failed
"""

import asyncio
import logging
import uuid

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.live_session import LiveSession, ProgressRecord
from app.models.user import User
from app.services.live import asr, coaching, language, pronunciation, scoring, speech, vision
from app.services.live._ml import available
from app.services.notifications import notify
from app.services.live.audio import to_16k_wav
from app.services.media import MediaError, detect_silences, wav_duration
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

PROGRESS_METRICS = (
    "fluency_score", "pronunciation_score", "eye_contact_score",
    "confidence_score", "posture_score", "overall_score",
)


async def analyze_recording(
    recording,
    work_dir,
    session_history_count: int,
    *,
    session_type: str = "Conversation",
    user_goal: str | None = None,
    previous: dict | None = None,
) -> tuple[dict, list[str]]:
    """Run every analysis stage on one recording. Returns (analysis, warnings)."""
    warnings: list[str] = []

    wav = await to_16k_wav(recording, work_dir / "audio_16k.wav")
    duration = wav_duration(wav)
    if duration < 1.0:
        raise MediaError("The recording is shorter than one second — please record again.")
    silences = await detect_silences(wav, min_duration=speech.INTER_WORD_PAUSE_SEC)
    if duration - sum(e - s for s, e in silences) < 1.0:
        raise MediaError("No speech was detected in the recording — check your microphone and try again.")

    # ── Speech ────────────────────────────────────────────────────────────
    asr_result = await asr.transcribe(wav, warnings)
    transcript = asr_result.transcript if asr_result else ""
    words = asr_result.word_timestamps if asr_result else []

    lang = language.detect_language_and_accent(transcript) if transcript else None
    fluency = speech.analyze_fluency(transcript, duration, words, silences) if transcript else None
    fillers = speech.detect_fillers(transcript, duration) if transcript else None
    stutter = speech.detect_stuttering(transcript, words, silences, duration, wav)

    pron = None
    if transcript:
        if available("transformers", "torch", "numpy"):
            try:
                pron = await asyncio.to_thread(pronunciation.assess, wav, transcript)
            except Exception as e:  # noqa: BLE001
                logger.exception("Pronunciation assessment failed")
                warnings.append(f"Pronunciation scoring failed ({e}).")
        else:
            warnings.append("Pronunciation scoring needs the local Wav2Vec2 model (requirements-ml.txt); skipped.")
    pron_score = language.adjust_pronunciation_for_accent(pron.score, lang) if pron and lang else None

    # ── Vision ────────────────────────────────────────────────────────────
    eye = posture = emotion = None
    if available("cv2", "mediapipe"):
        frames = await asyncio.to_thread(vision.sample_frames, str(recording), 60)
        if not frames:
            warnings.append("The recording has no readable video frames, so eye contact, posture and emotion were skipped.")
        else:
            for name, fn in (("Eye contact", vision.analyze_eye_contact), ("Posture", vision.analyze_posture)):
                try:
                    result = await asyncio.to_thread(fn, frames)
                except Exception as e:  # noqa: BLE001
                    logger.exception("%s analysis failed", name)
                    warnings.append(f"{name} analysis failed ({e}).")
                    continue
                if result is None:
                    warnings.append(f"{name}: no face/body was detected in the video.")
                elif name == "Eye contact":
                    eye = result
                else:
                    posture = result
            if available("transformers", "torch", "PIL"):
                try:
                    emotion = await asyncio.to_thread(vision.analyze_emotion, frames)
                    if emotion is None:
                        warnings.append("Facial emotion: no face was detected in the video.")
                except Exception as e:  # noqa: BLE001
                    logger.exception("Emotion analysis failed")
                    warnings.append(f"Facial emotion analysis failed ({e}).")
            else:
                warnings.append("Facial emotion needs transformers + torch (requirements-ml.txt); skipped.")
    else:
        warnings.append(
            "Vision analysis (eye contact, posture, emotion) needs OpenCV + MediaPipe "
            "(requirements-ml.txt); skipped."
        )

    # ── Scoring ───────────────────────────────────────────────────────────
    confidence = scoring.estimate_confidence(
        speaking_rate=fluency.speaking_rate if fluency else None,
        pause_frequency=fluency.pause_frequency if fluency else None,
        fluency_score=fluency.fluency_score if fluency else None,
        emotion_confidence=emotion.confidence_level if emotion else None,
        facial_tension=emotion.facial_tension if emotion else None,
        posture_score=posture.posture_score if posture else None,
        body_stability=posture.body_stability if posture else None,
    )
    comm = scoring.compute_communication_score({
        "Fluency": fluency.fluency_score if fluency else None,
        "Pronunciation": pron_score,
        "Confidence": confidence.confidence_score if confidence else None,
        "Eye Contact": eye.eye_contact_score if eye else None,
        "Posture": posture.posture_score if posture else None,
    })
    # Recommendations from what was actually measured (see coaching.py)
    candidates = coaching.build_candidates(
        fluency=speech.to_dict(fluency) if fluency else None,
        fillers=speech.to_dict(fillers) if fillers else None,
        stutter=speech.to_dict(stutter),
        pronunciation={**pron.to_dict(), "score": pron_score} if pron else None,
        eye=vision.as_dict(eye),
        posture=vision.as_dict(posture),
        emotion=vision.as_dict(emotion),
        duration_sec=duration,
        session_type=session_type,
        previous=previous,
    )
    recs = await coaching.build_plan(
        candidates=candidates,
        strengths=comm.strengths,
        session_type=session_type,
        user_goal=user_goal,
        session_history_count=session_history_count,
        transcript_excerpt=transcript,
        warnings=warnings,
    )

    analysis = {
        "transcript": transcript or None,
        "duration_sec": round(duration, 1),
        "language": lang.to_dict() if lang else None,
        "speech": {
            "fluency_score": fluency.fluency_score if fluency else None,
            "speaking_rate": fluency.speaking_rate if fluency else None,
            "pronunciation_score": pron_score,
            "stuttering_score": stutter.stuttering_score,
            "stuttering_severity": stutter.severity,
            "filler_count": fillers.total_fillers if fillers else None,
            "filler_per_minute": fillers.fillers_per_minute if fillers else None,
            "top_filler": fillers.top_filler if fillers else None,
            "pause_frequency": fluency.pause_frequency if fluency else None,
            "fluency_grade": fluency.grade if fluency else None,
        },
        "vision": {
            "eye_contact_score": eye.eye_contact_score if eye else None,
            "posture_score": posture.posture_score if posture else None,
            "dominant_emotion": emotion.dominant_emotion if emotion else None,
            "confidence_score": confidence.confidence_score if confidence else None,
            "confidence_label": confidence.label if confidence else None,
        },
        "communication_score": {
            "overall_score": comm.overall_score,
            "grade": comm.grade,
            "strengths": comm.strengths,
            "improvement_areas": comm.improvement_areas,
            "scored_on": comm.scored_on,
        },
        "recommendations": recs.to_dict(),
        # Full per-model output, for anyone who wants more than the summary above
        "details": {
            "asr_engine": asr_result.engine if asr_result else None,
            "fluency": speech.to_dict(fluency) if fluency else None,
            "fillers": speech.to_dict(fillers) if fillers else None,
            "stuttering": speech.to_dict(stutter),
            "pronunciation": pron.to_dict() if pron else None,
            "eye_contact": vision.as_dict(eye),
            "posture": vision.as_dict(posture),
            "emotion": vision.as_dict(emotion),
            "confidence": vision.as_dict(confidence),
        },
    }
    return analysis, warnings


async def run_live_analysis(live_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        live = (await db.execute(select(LiveSession).where(LiveSession.id == live_id))).scalar_one_or_none()
        if live is None or not live.recording_storage_path:
            logger.error("Live analysis started for unknown/unrecorded session %s", live_id)
            return
        try:
            history = (await db.execute(
                select(func.count()).select_from(LiveSession).where(LiveSession.user_id == live.user_id)
            )).scalar_one()
            # The user's last analysed session, so recommendations can show progress
            previous = (await db.execute(
                select(LiveSession.analysis)
                .where(LiveSession.user_id == live.user_id, LiveSession.status == "complete",
                       LiveSession.id != live.id, LiveSession.created_at < live.created_at)
                .order_by(LiveSession.created_at.desc()).limit(1)
            )).scalar_one_or_none()
            user = await db.get(User, live.user_id)
            recording = storage_service.get_absolute_path(live.recording_storage_path)
            analysis, warnings = await analyze_recording(
                recording, recording.parent, history,
                session_type=live.session_type,
                user_goal=user.communication_goal if user else None,
                previous=previous,
            )

            live.analysis = {"session_id": str(live.id), **analysis}
            live.warnings = warnings or None
            live.status = "complete"
            values = {
                "fluency_score": analysis["speech"]["fluency_score"],
                "pronunciation_score": analysis["speech"]["pronunciation_score"],
                "eye_contact_score": analysis["vision"]["eye_contact_score"],
                "confidence_score": analysis["vision"]["confidence_score"],
                "posture_score": analysis["vision"]["posture_score"],
                "overall_score": analysis["communication_score"]["overall_score"],
            }
            for name in PROGRESS_METRICS:
                if values[name] is not None:
                    db.add(ProgressRecord(
                        user_id=live.user_id, live_session_id=live.id,
                        metric_name=name, metric_value=float(values[name]),
                    ))
            overall = analysis["communication_score"]["overall_score"]
            notify(db, live.user_id, "live_analysis", f"Your {live.session_type.lower()} session results are ready",
                   (f"Overall score {overall:.0f}. " if overall is not None else "")
                   + (f"Focus next: {analysis['recommendations']['weekly_focus']}." if analysis["recommendations"]["exercises"] else ""),
                   f"/assessment?live={live.id}")
            await db.commit()
            logger.info("Live analysis ready for %s", live_id)
        except MediaError as e:
            await db.rollback()
            await db.refresh(live)
            live.status, live.error_detail = "failed", str(e)
            notify(db, live.user_id, "live_failed", "Session analysis failed", str(e), "/practice")
            await db.commit()
        except Exception as e:  # noqa: BLE001
            logger.exception("Live analysis crashed for %s", live_id)
            await db.rollback()
            await db.refresh(live)
            live.status, live.error_detail = "failed", f"Internal error: {e}"
            notify(db, live.user_id, "live_failed", "Session analysis failed", "Internal error — please try the session again.", "/practice")
            await db.commit()
