"""Mate, the in-app assistant (services/assistant.py): one reply per message."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_cloud_consent
from app.database import get_db
from app.limits import rate_limit
from app.models.user import User
from app.services import assistant

router = APIRouter(tags=["assistant"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    page: str | None = Field(default=None, max_length=120)   # where the user is, e.g. "/progress"


@router.post("/assistant/chat", dependencies=[Depends(rate_limit("assistant", 20))])
async def chat(body: ChatRequest, user: User = Depends(require_cloud_consent), db: AsyncSession = Depends(get_db)):
    """Mate's answer to the conversation so far (the last message is the user's)."""
    text = await assistant.reply(db, user, [m.model_dump() for m in body.messages], body.page)
    return {"reply": text}
