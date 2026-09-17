from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Any


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileResponse(BaseModel):
    id: str
    user_id: str
    age_group: str | None
    communication_goal: str | None
    skill_level: str
    challenges: Any

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    language: str | None = None
    communication_goal: str | None = None
    skill_level: str | None = None
    challenges: list[str] | None = None
