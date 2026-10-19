"""SQLAlchemy ORM model for user accounts (with their coaching profile)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.session import JSONType


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="en")

    # Coaching profile (set at registration / onboarding, editable on the profile page)
    age_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    communication_goal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skill_level: Mapped[str] = mapped_column(String(50), nullable=False, default="Beginner")
    challenges: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    # Who the AI is talking to, so questions and feedback fit (services/learner.py)
    study_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feedback_style: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Privacy (PDPA): when the user agreed to cloud processing (audio → Groq, text → Gemini);
    # None = not yet, and the routes that start cloud processing refuse (require_cloud_consent)
    cloud_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Raw recordings are deleted once their analysis succeeds, unless the user keeps them
    keep_recordings: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    live_sessions: Mapped[list["LiveSession"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
