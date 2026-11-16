"""Impromptu speaking: the learner gets a random topic, researches it for 5 minutes, talks about it
for 1-2 minutes, and the transcript is judged on how well they understood and explained the topic.
The browser transcribes the speech with /stt first; nothing here is stored."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_cloud_consent
from app.limits import rate_limit
from app.models.user import User
from app.services.ai import count_words, get_llm_client
from app.services.learner import learner_brief, with_brief
from app.services.live.speech import count_fillers
from app.services.practice_plans import _llm_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/impromptu", tags=["impromptu"])

MIN_WORDS = 20  # below this there's nothing to judge


class ImpromptuRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    transcript: str = Field(max_length=6000)
    duration_sec: float = Field(gt=0, le=600)


class _Judgement(BaseModel):
    accuracy: int = Field(ge=1, le=5)
    depth: int = Field(ge=1, le=5)
    coverage: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)
    structure: int = Field(ge=1, le=5)
    summary: str = Field(min_length=10, max_length=600)
    understood: list[str] = Field(default_factory=list, max_length=4)
    missed: list[str] = Field(default_factory=list, max_length=4)
    mistakes: list[str] = Field(default_factory=list, max_length=4)
    outline: list[str] = Field(default_factory=list, max_length=6)


JUDGE_SYSTEM = """You judge a 1-2 minute impromptu talk by an English learner who had 5 minutes to research a topic.
Judge their UNDERSTANDING of the topic from the transcript (speech-to-text: ignore spelling, fillers and grammar).
Rate 1-5:
- accuracy: are the facts and claims correct? (5 = nothing wrong, 1 = mostly wrong)
- depth: do they explain how and why, not just name things?
- coverage: do they touch the main aspects a well-informed person would mention?
- relevance: do they stay on the topic they were given?
- structure: a clear opening, points in a sensible order, a closing line.
Then: a 2-sentence summary starting with what they did well; up to 3 points they clearly understood (quote a few
of their words); up to 3 important points they missed; any factual mistakes (empty list if none, never invent
one); and a short outline of 3-5 points a strong 2-minute talk on this topic would cover.
Plain everyday English, short sentences, encouraging.
Return JSON only: {"accuracy": n, "depth": n, "coverage": n, "relevance": n, "structure": n, "summary": "...",
"understood": ["..."], "missed": ["..."], "mistakes": ["..."], "outline": ["..."]}"""


def understanding_score(j: _Judgement) -> float:
    """0-100 from the four understanding ratings (structure is reported, not counted): 1 → 0, 5 → 100."""
    return round((j.accuracy + j.depth + j.coverage + j.relevance - 4) / 16 * 100, 1)


@router.post("/evaluate", dependencies=[Depends(rate_limit("impromptu", 10))])
async def evaluate(body: ImpromptuRequest, user: User = Depends(require_cloud_consent)):
    words = count_words(body.transcript)
    fillers = sum(count_fillers(body.transcript).values())
    measured = {"words": words, "duration_sec": round(body.duration_sec, 1),
                "wpm": round(words / body.duration_sec * 60) if words else 0, "fillers": fillers}
    if words < MIN_WORDS:
        return {**measured, "judged": False,
                "summary": f"Only {words} word{'' if words == 1 else 's'} heard, too few to judge. Try again and keep talking for at least a minute."}
    if get_llm_client() is None:
        raise HTTPException(status_code=503, detail="The AI judge isn't available right now")
    try:
        j = await _llm_json(with_brief(JUDGE_SYSTEM, learner_brief(user)),
                            {"topic": body.topic, "transcript": body.transcript}, _Judgement, temperature=0.3)
    except Exception as e:  # noqa: BLE001 — provider error / rate limit
        logger.warning("Impromptu judge failed: %s", e)
        j = None
    if j is None:
        raise HTTPException(status_code=502, detail="The AI judge didn't answer, please try again")
    return {**measured, "judged": True, "understanding": understanding_score(j), **j.model_dump()}
