"""Live-session analysis pipeline (background job).

    recording → 16 kHz WAV → ASR (+ code-switch routing) → language detection
      → fluency / fillers / stuttering / pronunciation
      → eye contact / posture / emotion (video frames)
      → vocal variety / loudness / vocabulary / hedging / gestures / head stability
      → confidence → communication score → four pillars → recommendations
      → content feedback on what was said (interview answers / Q&A / language)
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
from app.services import practice_plans
from app.services.live import asr, coaching, extra_metrics, language, pronunciation, scoring, speech, vision
from app.services.live._ml import available
from app.services.live.talk import talk_feedback
from app.services.notifications import notify
from app.services.live.audio import to_16k_wav
from app.services.media import MediaError, detect_silences, wav_duration
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

PROGRESS_METRICS = (
    "fluency_score", "pronunciation_score", "eye_contact_score",
    "confidence_score", "posture_score", "overall_score",
    "voice_score", "language_score", "body_score", "presence_score",
)
PILLAR_METRICS = {"voice": "voice_score", "language": "language_score", "body": "body_score", "confidence": "presence_score"}


async def analyze_recording(
    recording,
    work_dir,
    session_history_count: int,
    *,
    session_type: str = "Conversation",
    user_goal: str | None = None,
    previous: dict | None = None,
    context: dict | None = None,
    turns: list[dict] | None = None,
    client_metrics: dict | None = None,
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

    # The content feedback (an LLM call on the turns) needs nothing measured from the
    # recording, so it runs alongside the speech and vision models instead of after them
    # A presentation talk is judged slide by slide from the transcript's word timings (after ASR)
    talk = (context or {}).get("kind") == "talk"
    content_task = None if talk else asyncio.create_task(practice_plans.content_feedback(session_type, context, turns))
    try:
        # Speech, then vision: running both model sets at once ran a 7.6 GB machine out of
        # memory (OOM-killed). Each stage still runs its own light parts in parallel.
        sp = await _speech_stage(wav, duration, silences, warnings)
        vi = await _vision_stage(recording, warnings)
    except BaseException:
        if content_task:
            content_task.cancel()
        raise
    asr_result, transcript, lang, fluency, fillers, stutter, pron, pron_score, prosody, lang_use = sp
    eye, posture, emotion, gestures = vi

    # ── Scoring ───────────────────────────────────────────────────────────
    # The user's own talking time (turn gaps excluded), so every count becomes a fair per-minute rate
    talk_min = speech._count_words(transcript) / fluency.speaking_rate if fluency and fluency.speaking_rate else None
    confidence = scoring.estimate_confidence(
        speaking_rate=fluency.speaking_rate if fluency else None,
        talk_minutes=talk_min,
        pause_frequency=fluency.pause_frequency if fluency else None,
        repetition_count=stutter.repetition_count if transcript else None,
        block_count=(stutter.block_count + stutter.prolongation_count) if transcript else None,
        fillers_per_minute=round(fillers.total_fillers / talk_min, 1) if fillers and talk_min else None,
        response_latency_sec=extra_metrics.median_latency(client_metrics),
        emotion_confidence=emotion.confidence_level if emotion else None,
        facial_tension=emotion.facial_tension if emotion else None,
        posture_score=posture.posture_score if posture else None,
        body_stability=posture.body_stability if posture else None,
        eye_contact_score=eye.eye_contact_score if eye else None,
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
        prosody=extra_metrics.as_dict(prosody),
        language_use=extra_metrics.as_dict(lang_use),
        response_latency_sec=extra_metrics.median_latency(client_metrics),
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
        # What was said, judged against the plan (interview answers, Q&A) or as language
        "content_feedback": (
            await talk_feedback(context, asr_result.word_timestamps if asr_result else [],
                                (client_metrics or {}).get("slide_times"), duration)
            if talk else await content_task
        ),
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
            "prosody": extra_metrics.as_dict(prosody),
            "language_use": extra_metrics.as_dict(lang_use),
            "gestures": extra_metrics.as_dict(gestures),
            "client": client_metrics,
        },
    }
    # The simple view: four pillars, each with its measured metrics
    analysis["pillars"] = extra_metrics.build_pillars(analysis, prosody, lang_use, gestures, client_metrics)
    return analysis, warnings


async def _speech_stage(wav, duration: float, silences, warnings: list[str]):
    """ASR, then everything that reads the words; prosody (audio only) runs alongside ASR."""
    async def prosody_part():
        if not available("librosa", "numpy"):
            warnings.append("Vocal variety and volume need librosa (requirements-ml.txt); skipped.")
            return None
        try:
            return await asyncio.to_thread(extra_metrics.analyze_prosody, wav)
        except Exception as e:  # noqa: BLE001
            logger.exception("Prosody analysis failed")
            warnings.append(f"Vocal variety / volume analysis failed ({e}).")
            return None

    prosody_task = asyncio.create_task(prosody_part())
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
    lang_use = extra_metrics.analyze_language_use(transcript) if transcript else None
    return asr_result, transcript, lang, fluency, fillers, stutter, pron, pron_score, await prosody_task, lang_use


async def _vision_stage(recording, warnings: list[str]):
    """Eye contact, posture, gestures and emotion: independent reads of the same frames, run in parallel."""
    if not available("cv2", "mediapipe"):
        warnings.append(
            "Vision analysis (eye contact, posture, emotion) needs OpenCV + MediaPipe "
            "(requirements-ml.txt); skipped."
        )
        return None, None, None, None
    frames = await asyncio.to_thread(vision.sample_frames, str(recording), 60)
    if not frames:
        warnings.append("The recording has no readable video frames, so eye contact, posture and emotion were skipped.")
        return None, None, None, None

    async def run(label: str, fn, *, none_msg: str | None = None):
        try:
            result = await asyncio.to_thread(fn, frames)
        except Exception as e:  # noqa: BLE001
            logger.exception("%s analysis failed", label)
            warnings.append(f"{label} analysis failed ({e}).")
            return None
        if result is None and none_msg:
            warnings.append(none_msg)
        return result

    async def emotion_part():
        if not available("transformers", "torch", "PIL"):
            warnings.append("Facial emotion needs transformers + torch (requirements-ml.txt); skipped.")
            return None
        return await run("Facial emotion", vision.analyze_emotion, none_msg="Facial emotion: no face was detected in the video.")

    # Posture and gestures share one MediaPipe Pose instance, which isn't thread-safe: run them in turn
    async def body_part():
        posture = await run("Posture", vision.analyze_posture, none_msg="Posture: no face/body was detected in the video.")
        return posture, await run("Gesture", extra_metrics.analyze_gestures)

    eye, (posture, gestures), emotion = await asyncio.gather(
        run("Eye contact", vision.analyze_eye_contact, none_msg="Eye contact: no face/body was detected in the video."),
        body_part(),
        emotion_part(),
    )
    return eye, posture, emotion, gestures


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
                context=live.context,
                turns=live.turns,
                client_metrics=live.client_metrics,
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
                **{name: analysis["pillars"][key]["score"] for key, name in PILLAR_METRICS.items()},
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
                   f"/results/{live.id}")
            await db.commit()
            logger.info("Live analysis ready for %s", live_id)
        except MediaError as e:
            await db.rollback()
            await db.refresh(live)
            live.status, live.error_detail = "failed", str(e)
            notify(db, live.user_id, "live_failed", "Session analysis failed", str(e), f"/results/{live.id}")
            await db.commit()
        except Exception as e:  # noqa: BLE001
            logger.exception("Live analysis crashed for %s", live_id)
            await db.rollback()
            await db.refresh(live)
            live.status, live.error_detail = "failed", f"Internal error: {e}"
            notify(db, live.user_id, "live_failed", "Session analysis failed", "Internal error — please try the session again.", f"/results/{live.id}")
            await db.commit()
