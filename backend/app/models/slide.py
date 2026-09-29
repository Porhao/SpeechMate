"""SQLAlchemy ORM model for individual slides within a session."""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Slide(Base):
    """One slide within a presentation session."""

    __tablename__ = "slides"
    __table_args__ = (
        UniqueConstraint("session_id", "slide_index", name="uq_slide_session_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_index: Mapped[int] = mapped_column(Integer, nullable=False)
    png_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Text extracted from the .pptx (used as VLM context and offline fallback)
    slide_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    script_source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # vlm | fallback
    audio_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    # elevenlabs_clone | openai_tts | espeak | silence
    audio_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Per-slide pipeline status: pending → rendered → scripted → synthesized | failed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    session: Mapped["Session"] = relationship(back_populates="slides")  # noqa: F821
