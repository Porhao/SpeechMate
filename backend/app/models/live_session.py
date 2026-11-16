"""SQLAlchemy ORM model for live practice sessions (camera + mic, AI partner)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, JSONType

LIVE_IN_PROGRESS_STATUSES = ("analyzing",)


class LiveSession(Base):
    """One live practice session: Conversation, Interview (mock), or Presentation (deck Q&A)."""

    __tablename__ = "live_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recording_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # active → (recording uploaded, analysis requested) analyzing → complete | failed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    # Full multimodal analysis result (speech, vision, language, score, recommendations)
    analysis: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Practice setup: interview details + question plan, or the deck + its Q&A plan
    context: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # What was said, turn by turn: [{role: user|assistant, text, t_sec}]
    turns: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    # Measured in the browser during the session (schemas/live.py ClientMetrics)
    client_metrics: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="live_sessions")  # noqa: F821


# Opened (a row is created as soon as the practice page loads) but never ended or recorded: not an attempt
NEVER_USED = and_(LiveSession.status == "active", LiveSession.duration_sec == 0, LiveSession.recording_storage_path.is_(None))


def results_link(live_id) -> str:
    """Where a session's notifications point (and how they're found again when it's deleted)."""
    return f"/results/{live_id}"

