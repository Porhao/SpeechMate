"""Impromptu speaking: judge a 1-2 minute talk on a random topic by how well the speaker understood
and explained it (the transcript comes from /stt; nothing is stored)."""

import logging

from pydantic import BaseModel, Field

from app.services.ai import llm_json
from app.services.learner import with_brief
from app.services.live.speech import count_fillers
from app.services.text import count_words

logger = logging.getLogger(__name__)

MIN_WORDS = 20  # below this there's nothing to judge


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


def verdict(score: float) -> str:
    return "Strong understanding" if score >= 75 else "Partial understanding" if score >= 50 else "Needs more research"


def measure(transcript: str, duration_sec: float) -> dict:
    words = count_words(transcript)
    return {"words": words, "duration_sec": round(duration_sec, 1),
            "wpm": round(words / duration_sec * 60) if words else 0, "fillers": sum(count_fillers(transcript).values())}


async def judge(topic: str, transcript: str, duration_sec: float, learner: str) -> dict | None:
    """The measured numbers plus the understanding judgement; `judged: false` when the talk is too short.
    None when the LLM is missing or fails (the caller says so)."""
    measured = measure(transcript, duration_sec)
    if measured["words"] < MIN_WORDS:
        n = measured["words"]
        return {**measured, "judged": False,
                "summary": f"Only {n} word{'' if n == 1 else 's'} heard, too few to judge. Try again and keep talking for at least a minute."}
    try:
        j = await llm_json(with_brief(JUDGE_SYSTEM, learner), {"topic": topic, "transcript": transcript}, _Judgement, temperature=0.3)
    except Exception as e:  # noqa: BLE001 — provider error / rate limit
        logger.warning("Impromptu judge failed: %s", e)
        return None
    if j is None:
        return None
    score = understanding_score(j)
    return {**measured, "judged": True, "understanding": score, "verdict": verdict(score), **j.model_dump()}
