import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    session_type: Mapped[str] = mapped_column(String(50))
    duration: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="sessions")  # type: ignore[name-defined]
    speech_analysis: Mapped["SpeechAnalysis"] = relationship(back_populates="session", uselist=False)
    vision_analysis: Mapped["VisionAnalysis"] = relationship(back_populates="session", uselist=False)
    ai_feedback: Mapped["AIFeedback"] = relationship(back_populates="session", uselist=False)


class SpeechAnalysis(Base):
    __tablename__ = "speech_analysis"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("practice_sessions.id"), index=True)
    fluency_score: Mapped[float] = mapped_column(Float, default=0.0)
    pronunciation_score: Mapped[float] = mapped_column(Float, default=0.0)
    speaking_rate: Mapped[float] = mapped_column(Float, default=0.0)
    filler_word_count: Mapped[int] = mapped_column(Integer, default=0)
    stuttering_score: Mapped[float] = mapped_column(Float, default=0.0)

    session: Mapped["PracticeSession"] = relationship(back_populates="speech_analysis")


class VisionAnalysis(Base):
    __tablename__ = "vision_analysis"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("practice_sessions.id"), index=True)
    eye_contact_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    posture_score: Mapped[float] = mapped_column(Float, default=0.0)
    emotion_label: Mapped[str] = mapped_column(String(50), default="neutral")

    session: Mapped["PracticeSession"] = relationship(back_populates="vision_analysis")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("practice_sessions.id"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    recommendations: Mapped[dict] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["PracticeSession"] = relationship(back_populates="ai_feedback")


class ProgressHistory(Base):
    __tablename__ = "progress_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    metric_name: Mapped[str] = mapped_column(String(100))
    metric_value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="progress")  # type: ignore[name-defined]


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    report_url: Mapped[str] = mapped_column(Text)
    report_type: Mapped[str] = mapped_column(String(50))

    user: Mapped["User"] = relationship(back_populates="reports")  # type: ignore[name-defined]
