"""Pydantic schemas for deck request/response payloads."""

import uuid
from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreateResponse(BaseModel):
    """Response after uploading a deck."""
    session_id: uuid.UUID
    status: str


class SessionStatusResponse(BaseModel):
    """Response for polling a deck's preparation."""
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    status: str
    slide_count: int | None = None
    slides_rendered: int = 0
    error_detail: str | None = None
    warnings: list[str] = []
    # Deck insights (summary, structure, key points, suggestions, Q&A plan)
    insights: dict | None = None
    # The practice script (services/script_writer.py), if one was written
    script: dict | None = None
    original_filename: str
    created_at: datetime
    updated_at: datetime


class ScriptRequest(BaseModel):
    minutes: float = Field(ge=1, le=60)
    style: Literal["full", "points"] = "full"


class SessionListItem(BaseModel):
    """Compact deck info for listing."""
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    original_filename: str
    status: str
    slide_count: int | None = None
    created_at: datetime
