"""In-process background job runner (v1 replacement for Celery/arq).

Keeps strong references to running tasks (asyncio only holds weak ones)
and caps how many pipelines run at the same time.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from sqlalchemy import update

from app.config import settings
from app.database import async_session_factory
from app.models.live_session import LIVE_IN_PROGRESS_STATUSES, LiveSession
from app.models.practice_session import PRACTICE_IN_PROGRESS_STATUSES, PracticeSession
from app.models.session import SESSION_IN_PROGRESS_STATUSES, Session

logger = logging.getLogger(__name__)

_running: set[asyncio.Task] = set()
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(max(settings.max_concurrent_jobs, 1))
    return _semaphore


async def _guarded(coro: Coroutine[Any, Any, None], name: str) -> None:
    async with _get_semaphore():
        try:
            await coro
        except Exception:
            logger.exception("Background job %s crashed", name)


def spawn(coro: Coroutine[Any, Any, None], name: str) -> asyncio.Task:
    """Schedule a background job. Commit any DB rows it needs *before* calling this."""
    task = asyncio.create_task(_guarded(coro, name), name=name)
    _running.add(task)
    task.add_done_callback(_running.discard)
    return task


async def wait_for_all(timeout: float | None = None) -> None:
    """Wait for all running jobs (used by tests and graceful shutdown)."""
    if _running:
        await asyncio.wait(set(_running), timeout=timeout)


async def fail_interrupted_jobs() -> None:
    """On startup, mark jobs orphaned by a previous restart as failed so they can be retried."""
    message = "Interrupted by a server restart — use the retry endpoint to run it again."
    async with async_session_factory() as db:
        s = await db.execute(
            update(Session)
            .where(Session.status.in_(SESSION_IN_PROGRESS_STATUSES))
            .values(status="failed", error_detail=message)
        )
        p = await db.execute(
            update(PracticeSession)
            .where(PracticeSession.status.in_(PRACTICE_IN_PROGRESS_STATUSES))
            .values(status="failed", error_detail=message)
        )
        live = await db.execute(
            update(LiveSession)
            .where(LiveSession.status.in_(LIVE_IN_PROGRESS_STATUSES))
            .values(status="failed", error_detail="Interrupted by a server restart — request the analysis again.")
        )
        await db.commit()
        if s.rowcount or p.rowcount or live.rowcount:
            logger.warning(
                "Marked %d session(s), %d practice run(s) and %d live analysis job(s) as interrupted",
                s.rowcount, p.rowcount, live.rowcount,
            )
