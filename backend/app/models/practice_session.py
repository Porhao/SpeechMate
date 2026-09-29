"""SQLAlchemy ORM model for practice/coaching sessions (Coach Agent)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.session import JSONType

PRACTICE_IN_PROGRESS_STATUSES = ("queued", "transcribing", "analyzing")


class PracticeSession(Base):
    """A user's practice recording attempt against a completed session."""

    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    audio_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    # whole_deck | per_slide
    recording_granularity: Mapped[str] = mapped_column(
        String(50), nullable=False, default="whole_deck"
    )
    # Set when recording_granularity == "per_slide"
    slide_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Pipeline status: queued → transcribing → analyzing → complete | failed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    feedback: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    audience_feedback: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="practice_sessions")  # noqa: F821
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        back_populates="practice_session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
