from pydantic import BaseModel
from datetime import datetime
from typing import Any


class StartSessionRequest(BaseModel):
    session_type: str


class EndSessionRequest(BaseModel):
    session_id: str
    duration: int


class SessionResponse(BaseModel):
    id: str
    user_id: str
    session_type: str
    duration: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SpeechAnalysisResponse(BaseModel):
    fluency_score: float
    pronunciation_score: float
    stuttering_score: float
    speaking_rate: float
    filler_word_count: int


class VisionAnalysisResponse(BaseModel):
    eye_contact: float
    confidence: float
    posture: float


class AnalyzeRequest(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    question: str
    history: list[dict[str, str]] = []


class ChatResponse(BaseModel):
    answer: str
