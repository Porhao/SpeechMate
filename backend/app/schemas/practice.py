"""Pydantic schemas for the Coach Agent (practice runs + chat)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PracticeCreateResponse(BaseModel):
    practice_id: uuid.UUID
    status: str


class PracticeResponse(BaseModel):
    practice_id: uuid.UUID
    session_id: uuid.UUID
    status: str
    recording_granularity: str
    slide_index: int | None = None
    error_detail: str | None = None
    warnings: list[str] = []
    transcript: str | None = None
    metrics: dict | None = None
    feedback: dict | None = None
    audience_feedback: dict | None = None
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime | None = None


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]
