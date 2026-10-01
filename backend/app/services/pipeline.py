"""Ideal Presentation Agent: the 4-stage pipeline, run as a background job.

    queued → processing_slides → generating_scripts → synthesizing_audio
           → assembling_video → complete   (or → failed with error_detail)

Every AI stage has a fallback, so the only hard failures are an unreadable
deck or a broken ffmpeg/LibreOffice install. Soft fallbacks are recorded in
`session.warnings` for the UI.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models.session import Session
from app.models.slide import Slide
from app.services import malaysian_tts
from app.services.deck_insights import analyse_deck, script_context
from app.services.notifications import notify
from app.services.ai import unload_local_model
from app.services.media import (
    MediaError,
    concat_segments,
    normalize_to_wav,
    render_slide_segment,
    wav_duration,
)
from app.services.script_generator import script_generator
from app.services.slide_processor import SlideProcessorError, slide_processor
from app.services.speech_synthesizer import SOURCE_LABELS, speech_synthesizer
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """A hard failure with a user-facing message."""


async def _set_status(db: AsyncSession, session: Session, status: str, **fields) -> None:
    session.status = status
    for key, value in fields.items():
        setattr(session, key, value)
    await db.commit()
    logger.info("Session %s → %s", session.id, status)


def _add_warning(session: Session, message: str) -> None:
    # Reassign (not append) so SQLAlchemy notices the JSON change
    session.warnings = [*(session.warnings or []), message]


async def run_ideal_presentation_pipeline(session_id: uuid.UUID) -> None:
    """Run the full Ideal Presentation Agent pipeline for a session."""
    async with async_session_factory() as db:
        session = (
            await db.execute(select(Session).where(Session.id == session_id))
        ).scalar_one_or_none()
        if session is None:
            logger.error("Pipeline started for unknown session %s", session_id)
            return

        try:
            slides = await _stage_process_slides(db, session)
            await _stage_analyze_content(db, session, slides)
            await _stage_generate_scripts(db, session, slides)
            await _stage_synthesize_audio(db, session, slides)
            await _stage_assemble_video(db, session, slides)
            await _set_status(db, session, "complete")
            notify(db, session.user_id, "deck_ready", "Your example presentation is ready",
                   f"“{session.original_filename}” — watch it, then record your practice.", f"/presentations/{session.id}")
            await db.commit()
        except (PipelineError, SlideProcessorError, MediaError) as e:
            logger.error("Pipeline failed for session %s: %s", session_id, e)
            await db.rollback()
            await db.refresh(session)
            await _set_status(db, session, "failed", error_detail=str(e))
            notify(db, session.user_id, "deck_failed", "Example presentation failed",
                   f"“{session.original_filename}”: {e}", f"/presentations/{session.id}")
            await db.commit()
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected pipeline error for session %s", session_id)
            await db.rollback()
            await db.refresh(session)
            await _set_status(db, session, "failed", error_detail=f"Internal error: {e}")
            notify(db, session.user_id, "deck_failed", "Example presentation failed",
                   f"“{session.original_filename}” hit an internal error — try Retry.", f"/presentations/{session.id}")
            await db.commit()


# ── Stage 1: Slide Processing ────────────────────────────────────────────────
async def _stage_process_slides(db: AsyncSession, session: Session) -> list[Slide]:
    await _set_status(
        db, session, "processing_slides",
        error_detail=None, warnings=None, video_storage_path=None, voice_cloning_used=None, insights=None,
    )
    # Retries start from a clean slate
    await db.execute(delete(Slide).where(Slide.session_id == session.id))
    await db.commit()

    png_paths = await slide_processor.convert_pptx_to_pngs(str(session.id), session.pptx_storage_path)
    texts = slide_processor.extract_slide_texts(session.pptx_storage_path)
    if texts and len(texts) != len(png_paths):
        logger.warning(
            "Slide text count (%d) != rendered pages (%d); text context may be misaligned",
            len(texts), len(png_paths),
        )

    slides = []
    for i, png in enumerate(png_paths, start=1):
        slide = Slide(
            session_id=session.id,
            slide_index=i,
            png_storage_path=storage_service.relative(png),
            slide_text=texts[i - 1] if i - 1 < len(texts) else None,
            status="rendered",
        )
        db.add(slide)
        slides.append(slide)
    session.slide_count = len(slides)
    await db.commit()
    return slides


# ── Stage 1b: Content analysis (deck insights) ──────────────────────────────
async def _stage_analyze_content(db: AsyncSession, session: Session, slides: list[Slide]) -> None:
    await _set_status(db, session, "analyzing_content")
    insights, warning = await analyse_deck([s.slide_text or "" for s in slides], session.requirement_prompt)
    session.insights = insights
    if warning:
        _add_warning(session, warning)
    await db.commit()


# ── Stage 2: Script Generation (VLM) ─────────────────────────────────────────
async def _stage_generate_scripts(db: AsyncSession, session: Session, slides: list[Slide]) -> None:
    await _set_status(db, session, "generating_scripts")
    scripts_dir = storage_service.ensure_session_dirs(str(session.id))["scripts"]

    previous: str | None = None
    fallback_count = 0
    for slide in slides:  # sequential on purpose: each slide sees the previous narration
        result = await script_generator.generate(
            image_path=storage_service.get_absolute_path(slide.png_storage_path),
            slide_index=slide.slide_index,
            slide_count=len(slides),
            slide_text=slide.slide_text or "",
            requirement_prompt=session.requirement_prompt,
            previous_script=previous,
            deck_context=script_context(session.insights, slide.slide_index),
        )
        slide.script_text = result.text
        slide.script_word_count = result.word_count
        slide.script_source = result.source
        slide.status = "scripted"
        fallback_count += result.source == "fallback"
        previous = result.text

        (scripts_dir / f"slide_{slide.slide_index}.json").write_text(json.dumps({
            "slide_index": slide.slide_index,
            "text": result.text,
            "word_count": result.word_count,
            "source": result.source,
            "model": result.model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
        await db.commit()  # per-slide commit → live "3/8 scripted" progress

    if fallback_count:
        _add_warning(
            session,
            f"{fallback_count} of {len(slides)} script(s) were built from slide text instead of the AI "
            "model (no LLM configured, or the model call failed).",
        )
        await db.commit()


# ── Stage 3: Speech Synthesis (voice cloning + fallbacks) ────────────────────
async def _stage_synthesize_audio(db: AsyncSession, session: Session, slides: list[Slide]) -> None:
    await _set_status(db, session, "synthesizing_audio")
    dirs = storage_service.ensure_session_dirs(str(session.id))

    sample_wav = None
    if session.voice_sample_storage_path:
        try:
            sample_wav = await normalize_to_wav(
                storage_service.get_absolute_path(session.voice_sample_storage_path),
                dirs["root"] / "voice_sample.wav",
            )
        except MediaError as e:
            _add_warning(session, f"Could not read the voice sample ({e}); using a standard voice.")

    # The slide scripts are written: free the local vision model before the TTS model loads
    await unload_local_model(settings.vlm_model)

    voice = await speech_synthesizer.prepare_voice(str(session.id), sample_wav, session.narrator_voice)
    sources: list[str] = []
    try:
        for slide in slides:
            out = dirs["audio"] / f"slide_{slide.slide_index}.wav"
            source = await speech_synthesizer.synthesize(slide.script_text or "", out, voice)
            slide.audio_storage_path = storage_service.relative(out)
            slide.audio_duration_sec = round(wav_duration(out), 3)
            slide.audio_source = source
            slide.status = "synthesized"
            sources.append(source)
            await db.commit()
    finally:
        await speech_synthesizer.cleanup_voice(voice)
        if malaysian_tts.is_available() and not malaysian_tts.keep_loaded():
            malaysian_tts.unload()

    session.voice_cloning_used = bool(sources) and all(s == "elevenlabs_clone" for s in sources)
    if not session.voice_cloning_used:
        if voice.clone_error and sample_wav is not None:
            _add_warning(session, f"{voice.clone_error}. A fallback voice was used instead.")
        used = sorted({SOURCE_LABELS[s] for s in sources if s != "elevenlabs_clone"})
        if used:
            _add_warning(session, f"Narration used {', '.join(used)}.")
    await db.commit()


# ── Stage 4: Video Assembly ──────────────────────────────────────────────────
async def _stage_assemble_video(db: AsyncSession, session: Session, slides: list[Slide]) -> None:
    await _set_status(db, session, "assembling_video")
    dirs = storage_service.ensure_session_dirs(str(session.id))
    segments_dir = dirs["root"] / "segments"

    segments = []
    for slide in slides:
        segments.append(await render_slide_segment(
            storage_service.get_absolute_path(slide.png_storage_path),
            storage_service.get_absolute_path(slide.audio_storage_path),
            segments_dir / f"slide_{slide.slide_index}.mp4",
            slide.audio_duration_sec or 1.0,
        ))

    video = await concat_segments(segments, dirs["root"] / "ideal_video.mp4")
    session.video_storage_path = storage_service.relative(video)
    await db.commit()
