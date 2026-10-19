"""SQLAlchemy ORM model for one rendered slide of a deck."""

import uuid

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Slide(Base):
    """One slide within a deck."""

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
    # Text extracted from the deck (what deck insights and the talk check read)
    slide_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="slides")  # noqa: F821
