"""SQLAlchemy ORM model for presentation sessions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# JSONB on Postgres, plain JSON elsewhere (e.g. SQLite in tests)
JSONType = JSON().with_variant(JSONB(), "postgresql")

# Statuses that mean the Ideal Presentation Agent is still working
SESSION_IN_PROGRESS_STATUSES = (
    "queued",
    "processing_slides",
    "generating_scripts",
    "synthesizing_audio",
    "assembling_video",
)


class Session(Base):
    """A presentation session: one uploaded deck + its Ideal Presentation Agent output."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Not tied to a user account yet: decks are shared by everyone using this instance
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    pptx_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    voice_sample_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pipeline status tracking
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Soft fallbacks (e.g. "voice cloning failed, used standard voice") — not failures
    warnings: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    voice_cloning_used: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    slide_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Output artifact
    video_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    slides: Mapped[list["Slide"]] = relationship(  # noqa: F821
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Slide.slide_index",
    )
    practice_sessions: Mapped[list["PracticeSession"]] = relationship(  # noqa: F821
        back_populates="session",
        cascade="all, delete-orphan",
    )
