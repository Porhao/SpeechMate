"""Coach Agent Stage 2: structured feedback.

Two lenses, as in the PresentCoach paper:
  * Coach (delivery): Sincere Encouragement + 1-3 Observation–Impact–Suggestion
    items, under 150 words of OIS in total.
  * Audience (reception): a simulated listener from the target audience reports
    clarity, engagement, confusion points and what they'd remember.

Both are requested as JSON, validated with Pydantic and re-prompted once on
bad output. If no LLM is configured (or it keeps failing) a rule-based
generator works from the metrics alone.
"""

import json
import logging

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings
from app.services.ai import count_words, get_llm_client, parse_json_object

logger = logging.getLogger(__name__)

OIS_MAX_WORDS = 150


# ── Schemas ──────────────────────────────────────────────────────────────────
class OISItem(BaseModel):
    slide_index: int | None = None
    observation: str = Field(min_length=3)
    impact: str = Field(min_length=3)
    suggestion: str = Field(min_length=3)


class CoachFeedback(BaseModel):
    encouragement: str = Field(min_length=3)
    observations: list[OISItem] = Field(min_length=1, max_length=3)
    source: str = "llm"

    def ois_word_count(self) -> int:
        return sum(
            count_words(f"{o.observation} {o.impact} {o.suggestion}") for o in self.observations
        )


class AudienceFeedback(BaseModel):
    audience_profile: str
    overall_impression: str
    clarity_score: int = Field(ge=1, le=5)
    engagement_score: int = Field(ge=1, le=5)
    engaging_moments: list[str] = Field(default_factory=list, max_length=3)
    confusing_moments: list[str] = Field(default_factory=list, max_length=3)
    key_takeaway: str
    questions_i_would_ask: list[str] = Field(default_factory=list, max_length=3)
    source: str = "llm"

    @field_validator("engaging_moments", "confusing_moments", "questions_i_would_ask", mode="before")
    @classmethod
    def _cap_lists(cls, v):
        return v[:3] if isinstance(v, list) else v


# ── Prompts ──────────────────────────────────────────────────────────────────
COACH_SYSTEM = f"""You are a warm, expert presentation coach. You compare a learner's practice recording against an ideal reference presentation of the same slides and give focused, actionable feedback.

You receive: the presenter's goal/audience, the ideal narration script, objective delivery metrics computed from the learner's audio, and (if available) a transcript of the learner's practice.

Return ONLY a JSON object:
{{
  "encouragement": "1-2 sentences of sincere, specific praise grounded in the data (never generic)",
  "observations": [
    {{
      "slide_index": <slide number or null>,
      "observation": "what specifically happened, citing numbers/quotes where possible",
      "impact": "why it matters for the audience",
      "suggestion": "one concrete thing to do differently next time, e.g. an exact phrase to try"
    }}
  ]
}}

Rules:
- 1 to 3 observations: only the most impactful issues, ordered by importance.
- The observation+impact+suggestion text of ALL items together must stay under {OIS_MAX_WORDS} words.
- Base every claim on the metrics or transcript. Do not invent problems with body language, slides or visuals — you only have audio.
- If there is no transcript, focus on pace, pauses and duration.
- Speak directly to the learner ("you"). Be kind but honest."""

AUDIENCE_SYSTEM = """You are role-playing a member of the presentation's target audience: {audience}.
You have just listened to a practice run of the presentation for the first time. You are NOT a coach — do not comment on technique jargon. React honestly as a listener: what kept your attention, where you got lost, and what you'll remember.

Return ONLY a JSON object:
{{
  "audience_profile": "who you are, in a few words",
  "overall_impression": "1-2 sentences in first person",
  "clarity_score": <1-5>,
  "engagement_score": <1-5>,
  "engaging_moments": ["up to 3 short items"],
  "confusing_moments": ["up to 3 short items"],
  "key_takeaway": "the one message you'd remember",
  "questions_i_would_ask": ["up to 3 questions you'd ask the speaker"]
}}

Base your reactions on the transcript (what was actually said) and the delivery metrics (e.g. a very fast pace or long silences make it harder to follow)."""


def build_analysis_input(
    *,
    requirement_prompt: str | None,
    ideal_scripts: list[tuple[int, str]],
    metrics: dict,
    transcript: str | None,
) -> str:
    parts = [
        f"PRESENTER'S GOAL / AUDIENCE: {requirement_prompt or 'not specified (assume a general audience)'}",
        "IDEAL NARRATION SCRIPT:\n" + "\n".join(f"[Slide {i}] {t}" for i, t in ideal_scripts),
        "DELIVERY METRICS (computed from the learner's audio):\n" + json.dumps(metrics, indent=2),
        "LEARNER'S TRANSCRIPT:\n" + (transcript if transcript else "(not available — no transcription configured)"),
    ]
    return "\n\n".join(parts)


async def _llm_json(system: str, user: str, validate) -> dict:
    """Ask for JSON, validate, re-prompt once with the error. Raises on second failure."""
    client = get_llm_client()
    assert client is not None
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    last_error: Exception | None = None
    for _ in range(2):
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        content = resp.choices[0].message.content or ""
        try:
            data = parse_json_object(content)
            return validate(data)
        except (ValueError, ValidationError) as e:
            last_error = e
            logger.warning("LLM returned invalid feedback JSON, re-prompting: %s", e)
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"That output was invalid: {e}. Return corrected JSON only."},
            ]
    assert last_error is not None
    raise last_error


def _validate_coach(data: dict) -> dict:
    fb = CoachFeedback.model_validate({**data, "source": "llm"})
    words = fb.ois_word_count()
    if words > OIS_MAX_WORDS:
        raise ValueError(
            f"observation+impact+suggestion text is {words} words; it must be under {OIS_MAX_WORDS}"
        )
    return fb.model_dump()


def _validate_audience(data: dict) -> dict:
    return AudienceFeedback.model_validate({**data, "source": "llm"}).model_dump()


async def generate_coach_feedback(analysis_input: str, metrics: dict) -> tuple[dict, str | None]:
    """Returns (feedback, warning). Falls back to rule-based feedback when needed."""
    if get_llm_client() is None:
        return rule_based_coach_feedback(metrics), (
            "Coach feedback was generated from metrics only (no LLM configured: set OPENAI_API_KEY or LLM_BASE_URL)."
        )
    try:
        return await _llm_json(COACH_SYSTEM, analysis_input, _validate_coach), None
    except Exception as e:  # noqa: BLE001
        logger.error("LLM coach feedback failed, using rule-based fallback: %s", e)
        return rule_based_coach_feedback(metrics), f"AI coach feedback failed ({e}); showing metric-based feedback."


async def generate_audience_feedback(
    analysis_input: str, metrics: dict, requirement_prompt: str | None
) -> tuple[dict, str | None]:
    audience = requirement_prompt or "a general, non-specialist audience"
    if get_llm_client() is None:
        return rule_based_audience_feedback(metrics, audience), None
    try:
        return await _llm_json(AUDIENCE_SYSTEM.format(audience=audience), analysis_input, _validate_audience), None
    except Exception as e:  # noqa: BLE001
        logger.error("LLM audience feedback failed, using rule-based fallback: %s", e)
        return rule_based_audience_feedback(metrics, audience), f"AI audience feedback failed ({e})."


# ── Rule-based fallbacks (no LLM) ────────────────────────────────────────────
def _mmss(sec: float) -> str:
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def _pace_issue(metrics: dict) -> tuple[float, OISItem] | None:
    wpm, ideal = metrics.get("wpm"), metrics.get("ideal_wpm")
    if wpm is None:
        ratio = metrics.get("duration_ratio")
        if ratio and ratio < 0.75:
            return 0.8, OISItem(
                observation=f"Your run took {metrics['duration_sec']}s versus {metrics['ideal_duration_sec']}s for the ideal version.",
                impact="Rushing compresses key points, so listeners have less time to absorb them.",
                suggestion="Slow down and pause briefly after each main idea.",
            )
        if ratio and ratio > 1.35:
            return 0.7, OISItem(
                observation=f"Your run took {metrics['duration_sec']}s versus {metrics['ideal_duration_sec']}s for the ideal version.",
                impact="A much longer delivery can lose the audience's attention.",
                suggestion="Rehearse each slide's core sentence so you can move on once it's said.",
            )
        return None
    target = ideal or 140
    diff = (wpm - target) / target
    if diff > 0.15 or wpm > 175:
        return 0.9 + diff, OISItem(
            observation=f"You spoke at about {wpm:.0f} words per minute, versus {target:.0f} in the ideal version.",
            impact="At that speed, listeners struggle to keep up with new information.",
            suggestion="Pause for a beat after each key point and let important numbers land.",
        )
    if diff < -0.2 or wpm < 100:
        return 0.7 - diff, OISItem(
            observation=f"You spoke at about {wpm:.0f} words per minute, versus {target:.0f} in the ideal version.",
            impact="A slow pace can make the talk feel hesitant and lose energy.",
            suggestion="Rehearse the ideal narration aloud a few times to internalize its rhythm.",
        )
    return None


def rule_based_coach_feedback(metrics: dict) -> dict:
    issues: list[tuple[float, OISItem]] = []

    if pace := _pace_issue(metrics):
        issues.append(pace)

    if metrics.get("long_pauses"):
        p = metrics["long_pauses"][0]
        issues.append((0.8 + p["duration_sec"] / 10, OISItem(
            observation=f"You paused for {p['duration_sec']}s at {_mmss(p['at_sec'])} ({len(metrics['long_pauses'])} pause(s) over 2s).",
            impact="Long silences break momentum and can signal uncertainty.",
            suggestion="Prepare a short bridge phrase, e.g. \"Here's why that matters\", to carry you to the next point.",
        )))

    fpm = metrics.get("fillers_per_minute") or 0
    if metrics.get("filler_word_count", 0) >= 4 and fpm >= 2:
        top = ", ".join(f'"{w}" ×{c}' for w, c in list(metrics["filler_words"].items())[:3])
        issues.append((0.6 + fpm / 10, OISItem(
            observation=f"You used {metrics['filler_word_count']} filler words ({top}).",
            impact="Frequent fillers distract listeners and reduce perceived confidence.",
            suggestion="Replace fillers with a silent one-second pause; silence sounds more confident.",
        )))

    coverage = metrics.get("script_coverage")
    if coverage is not None and coverage < 0.6:
        missed = ", ".join(metrics.get("missed_key_terms", [])[:4])
        issues.append((1.0 - coverage, OISItem(
            observation=f"You covered about {coverage:.0%} of the ideal script's key ideas; missing terms include {missed}.",
            impact="The audience may miss parts of your core message.",
            suggestion="Before each slide, name its one key idea to yourself and make sure you say it.",
        )))

    issues.sort(key=lambda x: -x[0])
    observations = [item for _, item in issues[:3]]
    if not observations:
        observations = [OISItem(
            observation="Your pace, pauses and content coverage were all close to the ideal version.",
            impact="The fundamentals are in place, so vocal variety is now what will make you memorable.",
            suggestion="Pick one key sentence per slide and practice stressing its most important word.",
        )]

    strengths = []
    if metrics.get("wpm") and metrics.get("ideal_wpm") and abs(metrics["wpm"] - metrics["ideal_wpm"]) / metrics["ideal_wpm"] <= 0.1:
        strengths.append(f"your pace of {metrics['wpm']:.0f} WPM closely matched the ideal delivery")
    if coverage is not None and coverage >= 0.75:
        strengths.append(f"you covered {coverage:.0%} of the key ideas")
    if metrics.get("filler_word_count") is not None and fpm < 1:
        strengths.append("you kept filler words to a minimum")
    if not metrics.get("long_pauses"):
        strengths.append("you kept a steady flow without long silences")
    encouragement = (
        f"Well done — {strengths[0]}." if strengths
        else "Great job completing a full practice run; every rehearsal builds fluency."
    )

    fb = CoachFeedback(encouragement=encouragement, observations=observations, source="rule_based")
    return fb.model_dump()


def rule_based_audience_feedback(metrics: dict, audience: str) -> dict:
    clarity, engagement = 4, 3
    confusing, engaging = [], []
    wpm = metrics.get("wpm")
    if wpm and wpm > 170:
        clarity -= 1
        confusing.append("The pace was fast, so I missed some details.")
    if metrics.get("long_pauses"):
        engagement -= 1
        confusing.append("A few long silences made me wonder if something went wrong.")
    coverage = metrics.get("script_coverage")
    if coverage is not None and coverage < 0.6:
        clarity -= 1
        confusing.append("I wasn't sure what the main message of some parts was.")
    if not confusing:
        engaging.append("The talk flowed steadily and was easy to follow.")
        engagement += 1

    return AudienceFeedback(
        audience_profile=audience,
        overall_impression=(
            "Without a transcript I can only react to how the talk sounded, not what was said."
            if not metrics.get("has_transcript")
            else "I could follow the talk; see the notes below on where I struggled."
        ),
        clarity_score=max(clarity, 1),
        engagement_score=max(min(engagement, 5), 1),
        engaging_moments=engaging,
        confusing_moments=confusing,
        key_takeaway="(needs an LLM to summarize what was said)",
        questions_i_would_ask=[],
        source="rule_based",
    ).model_dump()
