"""Deck preparation, run as a background job: render the slides, then understand them.

    queued → processing_slides → analyzing_content → complete   (or → failed with error_detail)

The user then presents the deck themselves (a live "talk" session that checks what they say
against each slide) and can rehearse the Q&A. Example scripts, narration and video were
removed on 2026-10-07. The insights step has a rule-based fallback, so the only hard failures
are an unreadable deck or a broken LibreOffice/pdftoppm install.
"""

import logging
import uuid

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.session import SESSION_IN_PROGRESS_STATUSES, Session
from app.models.slide import Slide
from app.models.user import User
from app.services import decks
from app.services.deck_insights import analyse_deck
from app.services.learner import learner_brief
from app.services.notifications import notify
from app.services import slide_processor
from app.services.tasks import fail_job
from app.services.storage import deck_folder, storage_service

logger = logging.getLogger(__name__)


async def _set_status(db: AsyncSession, session: Session, status: str, **fields) -> None:
    session.status = status
    for key, value in fields.items():
        setattr(session, key, value)
    await db.commit()
    logger.info("Session %s → %s", session.id, status)


def _add_warning(session: Session, message: str) -> None:
    # Reassign (not append) so SQLAlchemy notices the JSON change
    session.warnings = [*(session.warnings or []), message]


async def prepare_deck(session_id: uuid.UUID) -> None:
    """Prepare a deck for practice: render the slides, then understand them (insights + Q&A plan)."""
    async with async_session_factory() as db:
        session = await db.get(Session, session_id)
        if session is None:
            logger.error("Deck preparation started for unknown deck %s", session_id)
            return
        try:
            slides = await _stage_process_slides(db, session)
            await _stage_analyze_content(db, session, slides)
            await _set_status(db, session, "complete")
            notify(db, session.user_id, "deck_ready", "Your deck is ready to present",
                   f"“{session.original_filename}”: read the summary, then present it.", f"/presentations/{session.id}")
            await db.commit()
        except Exception as e:  # noqa: BLE001 — every failure ends as a failed deck the user can retry
            await fail_job(db, session, e, kind="deck_failed", title="Deck preparation failed",
                           link=f"/presentations/{session.id}", about=f"“{session.original_filename}”: ")


async def recover_after_restart() -> None:
    """On startup, mark decks a restart interrupted as failed, so the user can retry them."""
    async with async_session_factory() as db:
        result = await db.execute(update(Session).where(Session.status.in_(SESSION_IN_PROGRESS_STATUSES))
                                  .values(status="failed", error_detail="Interrupted by a server restart: press Retry."))
        await db.commit()
    if result.rowcount:
        logger.warning("Marked %d interrupted deck(s) as failed", result.rowcount)


# ── Slides ────────────────────────────────────────────────
async def _stage_process_slides(db: AsyncSession, session: Session) -> list[Slide]:
    await _set_status(
        db, session, "processing_slides",
        error_detail=None, warnings=None, insights=None,
    )
    # Retries start from a clean slate
    await db.execute(delete(Slide).where(Slide.session_id == session.id))
    await db.commit()

    png_paths = await slide_processor.render_slides(deck_folder(session.id), session.pptx_storage_path)
    texts = slide_processor.slide_texts(session.pptx_storage_path)
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
        )
        db.add(slide)
        slides.append(slide)
    session.slide_count = len(slides)
    await db.commit()
    return slides


# ── Content analysis (deck insights) ─────────────────────────────────────────
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
            owner = await db.get(User, session.user_id) if session.user_id else None
            await decks.qa_plan(session, learner_brief(owner))
            await db.commit()
        except Exception:  # noqa: BLE001 — the Q&A start builds it on demand instead
            logger.exception("Pre-building the Q&A plan failed for %s", session.id)
