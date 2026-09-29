import json
from types import SimpleNamespace

import pytest

from app.services import ai
from app.services.coach import feedback as fb_mod
from app.services.coach.feedback import (
    OIS_MAX_WORDS,
    CoachFeedback,
    generate_coach_feedback,
    rule_based_audience_feedback,
    rule_based_coach_feedback,
)

WORST_CASE_METRICS = {
    "duration_sec": 120.0, "ideal_duration_sec": 60.0, "duration_ratio": 2.0,
    "pause_count": 6, "total_pause_sec": 30.0, "longest_pause_sec": 8.0,
    "long_pauses": [{"at_sec": 65.0, "duration_sec": 8.0}], "ideal_wpm": 140.0,
    "has_transcript": True, "word_count": 400, "wpm": 200.0, "filler_word_count": 25,
    "filler_words": {"um": 12, "like": 8, "you know": 5}, "fillers_per_minute": 12.5,
    "script_coverage": 0.3, "missed_key_terms": ["eisenhower", "matrix", "calendar", "focus"],
}


def test_rule_based_feedback_respects_ois_limits():
    data = rule_based_coach_feedback(WORST_CASE_METRICS)
    parsed = CoachFeedback.model_validate(data)
    assert 1 <= len(parsed.observations) <= 3
    assert parsed.ois_word_count() < OIS_MAX_WORDS
    assert parsed.source == "rule_based"


def test_rule_based_feedback_when_everything_is_fine():
    good = {**WORST_CASE_METRICS, "wpm": 141.0, "long_pauses": [], "filler_word_count": 0,
            "fillers_per_minute": 0.0, "filler_words": {}, "script_coverage": 0.9, "duration_ratio": 1.0}
    data = rule_based_coach_feedback(good)
    assert len(data["observations"]) == 1
    assert "pace" in data["encouragement"]


def test_rule_based_audience_feedback_scores_in_range():
    data = rule_based_audience_feedback(WORST_CASE_METRICS, "first-year students")
    assert 1 <= data["clarity_score"] <= 5 and 1 <= data["engagement_score"] <= 5
    assert data["confusing_moments"]


def test_parse_json_object_handles_fences():
    assert ai.parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        ai.parse_json_object("[1, 2]")


class FakeLLM:
    """Minimal stand-in for AsyncOpenAI's chat.completions.create."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs["messages"])
        content = self.replies.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


async def test_llm_feedback_reprompts_when_too_long(monkeypatch):
    too_long = {"encouragement": "Nice.", "observations": [
        {"observation": "word " * 60, "impact": "word " * 60, "suggestion": "word " * 60}
    ]}
    good = {"encouragement": "Your opening was clear.", "observations": [
        {"slide_index": 2, "observation": "You rushed slide 2.", "impact": "Key data got lost.",
         "suggestion": "Pause after the statistic."}
    ]}
    fake = FakeLLM([json.dumps(too_long), json.dumps(good)])
    monkeypatch.setattr(fb_mod, "get_llm_client", lambda: fake)

    result, warning = await generate_coach_feedback("input", WORST_CASE_METRICS)
    assert warning is None
    assert result["source"] == "llm"
    assert result["observations"][0]["slide_index"] == 2
    assert len(fake.calls) == 2
    assert "must be under" in fake.calls[1][-1]["content"]


async def test_llm_feedback_falls_back_after_two_bad_replies(monkeypatch):
    fake = FakeLLM(["not json", "still not json"])
    monkeypatch.setattr(fb_mod, "get_llm_client", lambda: fake)
    result, warning = await generate_coach_feedback("input", WORST_CASE_METRICS)
    assert result["source"] == "rule_based"
    assert warning and "failed" in warning
