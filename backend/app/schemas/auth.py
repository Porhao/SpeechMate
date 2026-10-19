"""Pydantic schemas for accounts, auth tokens and the user profile."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

# The learner profile the AI adapts to (services/learner.py)
StudyLevel = Literal["Secondary", "Pre-university", "Undergraduate", "Postgraduate", "Working professional"]
FeedbackStyle = Literal["encouraging", "balanced", "direct"]


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    language: str = "en"
    communication_goal: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None  # now an httpOnly cookie (routers/auth.py); kept for old clients
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: str
    language: str
    age_group: str | None = None
    communication_goal: str | None = None
    skill_level: str
    challenges: list[str] = []
    study_level: str | None = None
    field_of_study: str | None = None
    feedback_style: str | None = None
    cloud_consent_at: datetime | None = None
    keep_recordings: bool = False
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    language: str | None = None
    age_group: str | None = None
    communication_goal: str | None = None
    skill_level: str | None = None
    challenges: list[str] | None = None
    study_level: StudyLevel | None = None
    field_of_study: str | None = Field(None, max_length=100)
    feedback_style: FeedbackStyle | None = None
    keep_recordings: bool | None = None


class ConsentRequest(BaseModel):
    accept: bool          # false withdraws consent


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
