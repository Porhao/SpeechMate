"""In-process background job runner (v1 replacement for Celery/arq), and how a job fails.

Keeps strong references to running tasks (asyncio only holds weak ones) and caps how many
pipelines run at the same time. Each pipeline marks its own rows interrupted by a restart.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.notifications import notify

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


class JobError(Exception):
    """A failure the user can act on: its message is shown to them as is."""


INTERNAL_ERROR = "Something went wrong on our side. Please try again."


async def fail_job(db: AsyncSession, row, error: Exception, *, kind: str, title: str, link: str, about: str = "") -> None:
    """Mark a background job's row (deck or live session) failed and tell its owner. A JobError's
    message is shown; anything else is logged in full and shown as INTERNAL_ERROR."""
    if isinstance(error, JobError):
        logger.warning("%s %s failed: %s", type(row).__name__, row.id, error)
        message = str(error)
    else:
        logger.error("%s %s crashed", type(row).__name__, row.id, exc_info=error)
        message = INTERNAL_ERROR
    await db.rollback()
    await db.refresh(row)
    row.status, row.error_detail = "failed", message
    notify(db, row.user_id, kind, title, f"{about}{message}", link)
    await db.commit()
