"""Pydantic schemas for session request/response payloads."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# --- Responses ---


class SlidesProgress(BaseModel):
    """Fine-grained slide processing progress."""
    rendered: int = 0
    scripted: int = 0
    synthesized: int = 0
    total: int = 0


class SessionCreateResponse(BaseModel):
    """Response after creating a new session."""
    session_id: uuid.UUID
    status: str


class SessionStatusResponse(BaseModel):
    """Response for polling session status."""
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    status: str
    slide_count: int | None = None
    slides_progress: SlidesProgress | None = None
    error_detail: str | None = None
    warnings: list[str] = []
    video_ready: bool = False
    voice_cloning_used: bool | None = None
    narrator_voice: str | None = None
    original_filename: str
    created_at: datetime
    updated_at: datetime


class SessionListItem(BaseModel):
    """Compact session info for listing."""
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    original_filename: str
    status: str
    slide_count: int | None = None
    created_at: datetime
