"""SQLAlchemy ORM models for live practice sessions (camera + mic, AI partner),
their per-metric progress history, and generated progress reports."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.session import JSONType

LIVE_IN_PROGRESS_STATUSES = ("analyzing",)


class LiveSession(Base):
    """One live practice session (Conversation / Interview / Presentation / Pronunciation)."""

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="live_sessions")  # noqa: F821
    progress: Mapped[list["ProgressRecord"]] = relationship(
        back_populates="live_session", cascade="all, delete-orphan"
    )


class ProgressRecord(Base):
    """One metric value from one analysed live session — the progress-over-time series."""

    __tablename__ = "progress_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    live_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("live_sessions.id", ondelete="CASCADE"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    live_session: Mapped["LiveSession"] = relationship(back_populates="progress")


class Report(Base):
    """A saved progress report (summary of a user's live sessions and metrics)."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, default="summary")
    content: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
