"""SQLAlchemy ORM model for user accounts (with their coaching profile)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, Uuid
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    live_sessions: Mapped[list["LiveSession"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
