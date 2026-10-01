"""Coach Agent pipeline, run as a background job per practice recording.

    queued → transcribing → analyzing → complete   (or → failed)
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.practice_session import PracticeSession
from app.models.session import Session
from app.models.slide import Slide
from app.services.coach.feedback import (
    build_analysis_input,
    generate_audience_feedback,
    generate_coach_feedback,
)
from app.services.coach.metrics import compute_metrics
from app.services.deck_insights import coach_context
from app.services.notifications import notify
from app.services.coach.transcription import transcribe
from app.services.media import SLIDE_GAP_SEC, MediaError, detect_silences, normalize_to_wav, wav_duration
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


async def _set_status(db: AsyncSession, practice: PracticeSession, status: str, **fields) -> None:
    practice.status = status
    for key, value in fields.items():
        setattr(practice, key, value)
    await db.commit()


async def _notify_failed(db: AsyncSession, practice: PracticeSession, reason: str) -> None:
    owner = (await db.execute(select(Session.user_id).where(Session.id == practice.session_id))).scalar_one_or_none()
    notify(db, owner, "practice_failed", "Practice analysis failed", reason, f"/presentations/{practice.session_id}")
    await db.commit()


def reference_slides(slides: list[Slide], practice: PracticeSession) -> list[Slide]:
    """The ideal slides this practice run should be compared against."""
    if practice.recording_granularity == "per_slide" and practice.slide_index:
        return [s for s in slides if s.slide_index == practice.slide_index]
    return slides


async def run_coach_pipeline(practice_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        practice = (
            await db.execute(select(PracticeSession).where(PracticeSession.id == practice_id))
        ).scalar_one_or_none()
        if practice is None:
            logger.error("Coach pipeline started for unknown practice %s", practice_id)
            return

        warnings: list[str] = []
        try:
            session = (
                await db.execute(select(Session).where(Session.id == practice.session_id))
            ).scalar_one()
            slides = list((
                await db.execute(
                    select(Slide).where(Slide.session_id == session.id).order_by(Slide.slide_index)
                )
            ).scalars())
            ref = reference_slides(slides, practice)

            # ── Stage 1a: normalize + transcribe ──────────────────────────
            await _set_status(db, practice, "transcribing", error_detail=None)
            src = storage_service.get_absolute_path(practice.audio_storage_path)
            wav = await normalize_to_wav(src, src.parent / "user_audio.wav")
            duration = wav_duration(wav)
            if duration < 1.0:
                raise MediaError("The recording is shorter than one second — please record again.")

            transcript = None
            try:
                transcript = await transcribe(wav)
                if transcript is None:
                    warnings.append(
                        "No transcription available (install requirements-ml.txt or set OPENAI_API_KEY): word-level metrics "
                        "(pace, fillers, content coverage) were skipped."
                    )
            except Exception as e:  # noqa: BLE001
                logger.error("Transcription failed for practice %s: %s", practice_id, e)
                warnings.append(f"Transcription failed ({e}); word-level metrics were skipped.")

            # ── Stage 1b: deterministic metrics ───────────────────────────
            await _set_status(db, practice, "analyzing", transcript=transcript)
            silences = await detect_silences(wav)
            speech_sec = duration - sum(end - start for start, end in silences)
            if speech_sec < 1.0:
                raise MediaError(
                    "No speech was detected in the recording — check your microphone and record again."
                )
            ideal_text = " ".join(s.script_text or "" for s in ref)
            key_points = {x.get("slide_index"): x.get("key_point") for x in (session.insights or {}).get("slides", [])}
            ideal_duration = sum((s.audio_duration_sec or 0) + SLIDE_GAP_SEC for s in ref) or None
            metrics = compute_metrics(
                duration_sec=duration,
                silences=silences,
                transcript=transcript,
                ideal_text=ideal_text,
                ideal_duration_sec=ideal_duration,
                slides=[(s.slide_index, s.script_text or "", key_points.get(s.slide_index)) for s in ref],
            )
            practice.metrics = metrics
            await db.commit()

            # ── Stage 2: OIS coach feedback + audience lens ───────────────
            analysis_input = build_analysis_input(
                requirement_prompt=session.requirement_prompt,
                ideal_scripts=[(s.slide_index, s.script_text or "") for s in ref],
                metrics=metrics,
                transcript=transcript,
            )
            # What the deck is about, so feedback can judge content, not just delivery
            if session.insights:
                analysis_input = coach_context(session.insights) + "\n\n" + analysis_input
            feedback, warn = await generate_coach_feedback(analysis_input, metrics)
            if warn:
                warnings.append(warn)
            audience, warn = await generate_audience_feedback(
                analysis_input, metrics, session.requirement_prompt
            )
            if warn:
                warnings.append(warn)

            await _set_status(
                db, practice, "complete",
                feedback=feedback, audience_feedback=audience, warnings=warnings or None,
            )
            notify(db, session.user_id, "practice_feedback", "Your practice feedback is ready",
                   f"Coaching on your {'slide ' + str(practice.slide_index) if practice.slide_index else 'whole-deck'} "
                   f"attempt of “{session.original_filename}”.", f"/presentations/{session.id}")
            await db.commit()
            logger.info("Coach feedback ready for practice %s", practice_id)

        except MediaError as e:
            logger.error("Coach pipeline failed for practice %s: %s", practice_id, e)
            await db.rollback()
            await db.refresh(practice)
            await _set_status(db, practice, "failed", error_detail=str(e), warnings=warnings or None)
            await _notify_failed(db, practice, str(e))
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected coach pipeline error for practice %s", practice_id)
            await db.rollback()
            await db.refresh(practice)
            await _set_status(
                db, practice, "failed", error_detail=f"Internal error: {e}", warnings=warnings or None
            )
            await _notify_failed(db, practice, "internal error — please record again")
