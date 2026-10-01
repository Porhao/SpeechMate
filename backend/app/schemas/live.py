"""Pydantic schemas for live practice sessions, progress, reports and chat/TTS."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# The three practice functions. "Presentation" is the Q&A rehearsal on an uploaded deck.
SESSION_TYPES = ("Conversation", "Interview", "Presentation")


class InterviewSetup(BaseModel):
    """What the candidate tells us so the interviewer can curate the questions."""

    position: str = Field(min_length=2, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    level: Literal["internship", "graduate", "junior", "mid", "senior"] = "graduate"
    interview_type: Literal["behavioural", "technical", "mixed"] = "mixed"
    background: str | None = Field(default=None, max_length=2000)
    job_description: str | None = Field(default=None, max_length=4000)
    resume_text: str | None = Field(default=None, max_length=8000)


class PlanQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=400)
    assesses: str = ""
    look_for: list[str] = []
    slide_index: int | None = None


class PracticePlan(BaseModel):
    intro: str = Field(min_length=3, max_length=800)
    questions: list[PlanQuestion] = Field(min_length=1, max_length=12)
    source: str = "rules"


class LiveStartRequest(BaseModel):
    session_type: Literal["Conversation", "Interview", "Presentation"]
    topic: str | None = Field(default=None, max_length=200)
    # Interview: the setup, plus the plan the user previewed (built here if omitted)
    interview: InterviewSetup | None = None
    plan: PracticePlan | None = None
    # Presentation: the deck to rehearse Q&A on (its insights curate the questions)
    deck_id: uuid.UUID | None = None


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)
    t_sec: float | None = None


class LiveEndRequest(BaseModel):
    duration_sec: int = Field(ge=0)
    turns: list[Turn] = Field(default=[], max_length=200)
    # Browser-side measurements, e.g. {"gaze_tunneling": 0.42, "response_latency_sec": [1.2, 0.8]}
    client_metrics: dict | None = None


class LiveSessionResponse(BaseModel):
    id: uuid.UUID
    session_type: str
    duration_sec: int
    status: str
    has_recording: bool
    error_detail: str | None = None
    warnings: list[str] = []
    analysis: dict | None = None
    context: dict | None = None
    turns: list | None = None
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
    # A planned Interview / Presentation Q&A session: the partner follows its question plan
    live_id: uuid.UUID | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str | None = None
