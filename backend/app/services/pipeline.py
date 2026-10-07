"""Deck preparation, run as a background job: render the slides, then understand them.

    queued → processing_slides → analyzing_content → complete   (or → failed with error_detail)

The user then presents the deck themselves (a live "talk" session that checks what they say
against each slide) and can rehearse the Q&A. Example scripts, narration and video were
removed on 2026-10-07. The insights step has a rule-based fallback, so the only hard failures
are an unreadable deck or a broken LibreOffice/pdftoppm install.
"""

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.session import Session
from app.models.slide import Slide
from app.services import practice_plans
from app.services.deck_insights import analyse_deck
from app.services.media import MediaError
from app.services.notifications import notify
from app.services.slide_processor import SlideProcessorError, slide_processor
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
    """Prepare a deck for practice: render the slides, then understand them (insights + Q&A plan).
    The user presents it themselves; there's no example narration or video any more (2026-10-07),
    so the script / narration / video stages below no longer run."""
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
            await _set_status(db, session, "complete")
            notify(db, session.user_id, "deck_ready", "Your deck is ready to present",
                   f"“{session.original_filename}”: read the summary, then present it.", f"/presentations/{session.id}")
            await db.commit()
        except (PipelineError, SlideProcessorError, MediaError) as e:
            logger.error("Pipeline failed for session %s: %s", session_id, e)
            await db.rollback()
            await db.refresh(session)
            await _set_status(db, session, "failed", error_detail=str(e))
            notify(db, session.user_id, "deck_failed", "Deck preparation failed",
                   f"“{session.original_filename}”: {e}", f"/presentations/{session.id}")
            await db.commit()
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected pipeline error for session %s", session_id)
            await db.rollback()
            await db.refresh(session)
            await _set_status(db, session, "failed", error_detail=f"Internal error: {e}")
            notify(db, session.user_id, "deck_failed", "Deck preparation failed",
                   f"“{session.original_filename}” hit an internal error: try Retry.", f"/presentations/{session.id}")
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
    # Prepare the Q&A rehearsal's question plan now (an LLM call of ~1 min on CPU), so
    # "Start Q&A" opens instantly instead of waiting for it
    if insights:
        try:
            title = session.original_filename.rsplit(".", 1)[0]
            plan = await practice_plans.build_qa_plan(title, insights, session.requirement_prompt)
            session.insights = {**insights, "qa_plan": plan}  # a new dict, so the JSON column is saved
            await db.commit()
        except Exception:  # noqa: BLE001 — the Q&A start builds it on demand instead
            logger.exception("Pre-building the Q&A plan failed for %s", session.id)
