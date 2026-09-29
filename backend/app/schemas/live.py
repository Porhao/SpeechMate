"""Pydantic schemas for live practice sessions, progress, reports and chat/TTS."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SESSION_TYPES = ("Conversation", "Interview", "Presentation", "Pronunciation")


class LiveStartRequest(BaseModel):
    session_type: Literal["Conversation", "Interview", "Presentation", "Pronunciation"]


class LiveEndRequest(BaseModel):
    duration_sec: int = Field(ge=0)


class LiveSessionResponse(BaseModel):
    id: uuid.UUID
    session_type: str
    duration_sec: int
    status: str
    has_recording: bool
    error_detail: str | None = None
    warnings: list[str] = []
    analysis: dict | None = None
    created_at: datetime


class ProgressRecordOut(BaseModel):
    id: uuid.UUID
    live_session_id: uuid.UUID
    metric_name: str
    metric_value: float
    recorded_at: datetime


class ReportOut(BaseModel):
    id: uuid.UUID
    report_type: str
    report_url: str
    content: dict
    created_at: datetime


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ConversationRequest(BaseModel):
    messages: list[ConversationMessage]
    mode: str = "Conversation"
    topic: str | None = None


class CoachQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[ConversationMessage] = []


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str | None = None
