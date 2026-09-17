import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")
    language: Mapped[str] = mapped_column(String(50), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)
    sessions: Mapped[list["PracticeSession"]] = relationship(back_populates="user")
    progress: Mapped[list["ProgressHistory"]] = relationship(back_populates="user")
    reports: Mapped[list["Report"]] = relationship(back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    age_group: Mapped[str] = mapped_column(String(50), nullable=True)
    communication_goal: Mapped[str] = mapped_column(String(100), nullable=True)
    skill_level: Mapped[str] = mapped_column(String(50), default="Beginner")
    challenges: Mapped[dict] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship(back_populates="profile")
