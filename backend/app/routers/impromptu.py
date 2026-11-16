"""Impromptu speaking: judge a talk on a random topic (see services/impromptu.py)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_cloud_consent
from app.limits import rate_limit
from app.models.user import User
from app.services import impromptu
from app.services.ai import get_llm_client
from app.services.learner import learner_brief

router = APIRouter(prefix="/impromptu", tags=["impromptu"])


class ImpromptuRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    transcript: str = Field(max_length=6000)
    duration_sec: float = Field(gt=0, le=600)


@router.post("/evaluate", dependencies=[Depends(rate_limit("impromptu", 10))])
async def evaluate(body: ImpromptuRequest, user: User = Depends(require_cloud_consent)):
    result = await impromptu.judge(body.topic, body.transcript, body.duration_sec, learner_brief(user))
    if result is None:
        if get_llm_client() is None:
            raise HTTPException(status_code=503, detail="The AI judge isn't available right now")
        raise HTTPException(status_code=502, detail="The AI judge didn't answer, please try again")
    return result
