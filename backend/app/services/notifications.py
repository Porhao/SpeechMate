"""Create in-app notifications (the caller commits)."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

logger = logging.getLogger(__name__)


def notify(db: AsyncSession, user_id: uuid.UUID | None, kind: str, title: str, body: str = "", link: str | None = None) -> None:
    """Queue a notification for `user_id` (no-op for anonymous work)."""
    if user_id is None:
        return
    db.add(Notification(user_id=user_id, kind=kind, title=title[:200], body=body, link=link))
