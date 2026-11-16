"""Pydantic schemas for live practice sessions, progress, reports and chat/TTS."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# The recorded practice functions ("Presentation" = talk or Q&A on an uploaded deck); the frontend's
# SessionType (frontend/types/index.ts) lists the same three.
SessionType = Literal["Conversation", "Interview", "Presentation"]
MAX_RESUME_CHARS = 8000


class InterviewSetup(BaseModel):
    """What the candidate tells us so the interviewer can curate the questions."""

    position: str = Field(min_length=2, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    level: Literal["internship", "graduate", "junior", "mid", "senior"] = "graduate"
    interview_type: Literal["behavioural", "technical", "mixed"] = "mixed"
    background: str | None = Field(default=None, max_length=2000)
    job_description: str | None = Field(default=None, max_length=4000)
    resume_text: str | None = Field(default=None, max_length=MAX_RESUME_CHARS)


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
    session_type: SessionType
    topic: str | None = Field(default=None, max_length=200)
    # Interview: the setup, plus the plan the user previewed (built here if omitted)
    interview: InterviewSetup | None = None
    plan: PracticePlan | None = None
    # Presentation: the deck. "talk" = the user presents it (slides they control; what they say is
    # checked against each slide); "qa" = the audience Q&A rehearsal (questions from the insights)
    deck_id: uuid.UUID | None = None
    presentation_mode: Literal["talk", "qa"] = "qa"
    # "talk" only: practise the deck's script (Script page); the results add script coverage and timing
    use_script: bool = False


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)
    t_sec: float | None = None


class SlideTime(BaseModel):
    slide_index: int
    t_sec: float  # on the recording's clock (clamped by live/talk.py)


class ClientMetrics(BaseModel):
    """What only the browser can measure (frontend/app/(app)/session/page.tsx sends it at the end)."""
    response_latency_sec: list[float] = Field(default=[], max_length=500)  # end of the AI's turn → first sound
    stt_audio_sec: list[float] = Field(default=[], max_length=500)          # each live turn sent to speech recognition
    slide_times: list[SlideTime] = Field(default=[], max_length=2000)       # talk mode: when each slide came up


class LiveEndRequest(BaseModel):
    duration_sec: int = Field(ge=0)
    turns: list[Turn] = Field(default=[], max_length=200)
    client_metrics: ClientMetrics | None = None


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


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ConversationRequest(BaseModel):
    messages: list[ConversationMessage] = Field(max_length=50)  # the partner reads the last 12
    mode: SessionType = "Conversation"
    topic: str | None = None
    # A planned Interview / Presentation Q&A session: the partner follows its question plan
    live_id: uuid.UUID | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
