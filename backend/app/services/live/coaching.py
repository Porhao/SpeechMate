"""Evidence-based improvement recommendations for a live session.

Every recommendation is built from something that was actually measured in this
recording — the number or moment it's based on (`evidence`), why it matters to a
listener (`why`), one concrete drill (`drill`) and a measurable target relative to
the current value (`target`). Candidates are ranked by how far the metric is from a
comfortable range, and compared with the user's previous session when there is one.

When an LLM is configured, it picks and phrases the top three for this user (their
goal and session type) — but only from these measured candidates, so it can't invent
an issue that wasn't observed. Otherwise the ranked rule-based list is used as-is.
"""

import json
import logging
from dataclasses import asdict, dataclass, field

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.ai import get_llm_client, parse_json_object

logger = logging.getLogger(__name__)

MAX_ITEMS = 3


@dataclass
class Recommendation:
    area: str            # pace | pauses | fillers | repetitions | pronunciation | eye_contact | posture | expression | vocal_variety | volume | hedging | response_time | length
    title: str
    evidence: str        # what was measured, with numbers / moments
    why: str             # why it matters to the listener
    drill: str           # one concrete exercise (5–10 minutes)
    target: str          # measurable goal for next session
    severity: float      # 0–1, how far from a comfortable range
    practice_type: str = "Conversation"
    daily_minutes: int = 10

    @property
    def priority(self) -> str:
        return "High" if self.severity >= 0.6 else "Medium" if self.severity >= 0.3 else "Low"


@dataclass
class CoachingPlan:
    exercises: list[dict] = field(default_factory=list)
    summary: str = ""
    weekly_focus: str = ""
    daily_target_minutes: int = 10
    next_session_type: str = "Conversation"
    tips: list[str] = field(default_factory=list)
    progress_forecast: str = ""
    source: str = "rules"   # rules | llm

    def to_dict(self) -> dict:
        return asdict(self)


def _mmss(sec: float | None) -> str:
    if sec is None:
        return "?"
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _trend(name: str, now: float | None, before: float | None, lower_is_better: bool, unit: str = "") -> str:
    if now is None or before is None:
        return ""
    better = now < before if lower_is_better else now > before
    fmt = (lambda v: f"{v:.0f}") if max(abs(now), abs(before)) >= 20 else (lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    if fmt(now) == fmt(before):
        return f" Same as last session ({fmt(before)}{unit})."
    return f" {'Better' if better else 'Worse'} than last session ({fmt(before)}{unit} → {fmt(now)}{unit})."


def build_candidates(
    *,
    fluency: dict | None,
    fillers: dict | None,
    stutter: dict | None,
    pronunciation: dict | None,
    eye: dict | None,
    posture: dict | None,
    emotion: dict | None,
    duration_sec: float,
    session_type: str,
    previous: dict | None = None,
    prosody: dict | None = None,
    language_use: dict | None = None,
    response_latency_sec: float | None = None,
) -> list[Recommendation]:
    """Every measured issue as a ranked recommendation (most severe first)."""
    prev_speech = (previous or {}).get("speech") or {}
    prev_vision = (previous or {}).get("vision") or {}
    practice = "Presentation" if session_type in ("Presentation", "Interview") else "Conversation"
    out: list[Recommendation] = []

    # ── Pace ──
    if fluency and fluency.get("speaking_rate"):
        wpm = fluency["speaking_rate"]
        trend = _trend("pace", wpm, prev_speech.get("speaking_rate"), lower_is_better=wpm > 160, unit=" wpm")
        if wpm > 165:
            out.append(Recommendation(
                "pace", "Slow down your delivery",
                f"You spoke at {wpm:.0f} words per minute; 120–160 is easy to follow.{trend}",
                "At this speed listeners miss key points and you have no room to breathe or emphasise.",
                "Take a 6-sentence paragraph you know. Read it aloud marking a slash after every sentence and "
                "pause one full breath at each slash. Record it twice: the second take should feel slow to you.",
                f"Under {max(150, int(wpm - 15))} wpm next session (now {wpm:.0f}).",
                _clamp01((wpm - 160) / 50), practice, 10))
        elif wpm < 110:
            out.append(Recommendation(
                "pace", "Bring more energy to your pace",
                f"You spoke at {wpm:.0f} words per minute; 120–160 sounds natural.{trend}",
                "A slow pace can sound hesitant and makes it harder for listeners to stay engaged.",
                "Pick a topic you know well and explain it in 60 seconds, then explain it again in 45 seconds "
                "without dropping any point.",
                f"Above {min(125, int(wpm + 15))} wpm next session (now {wpm:.0f}).",
                _clamp01((110 - wpm) / 40), practice, 10))

    # ── Long pauses / blocks ──
    blocks = [e for e in (stutter or {}).get("detected_events", []) if e.get("type") == "Block"]
    if blocks:
        times = ", ".join(_mmss(b.get("start_time")) for b in blocks[:4])
        longest = max((b.get("end_time") or 0) - (b.get("start_time") or 0) for b in blocks)
        out.append(Recommendation(
            "pauses", "Bridge long silences",
            f"{len(blocks)} mid-sentence silence(s) of 1.2 s or more (at {times}); the longest was {longest:.1f} s.",
            "Short pauses add emphasis, but long ones mid-sentence read as losing your thread.",
            "Prepare three bridge phrases (\"The key point is…\", \"Let me put it another way…\", "
            "\"Coming back to…\"). Answer 5 practice questions and use a bridge whenever you feel a blank.",
            f"At most {max(0, len(blocks) - 1)} silence(s) over 1.2 s next session (now {len(blocks)}).",
            _clamp01(len(blocks) / 5 + longest / 8), practice, 10))

    # ── Fillers ──
    if fillers and fillers.get("total_fillers"):
        fpm = fillers.get("fillers_per_minute") or 0
        if fpm >= 3:
            top = ", ".join(f"“{w}” ×{n}" for w, n in list((fillers.get("filler_breakdown") or {}).items())[:3])
            trend = _trend("fillers", fpm, prev_speech.get("filler_per_minute"), lower_is_better=True, unit="/min")
            out.append(Recommendation(
                "fillers", "Swap filler words for a silent pause",
                f"{fillers['total_fillers']} filler words ({fpm:.1f} per minute): {top}.{trend}",
                "Fillers dilute your message and make you sound less certain than you are.",
                f"Answer 3 questions for 60 seconds each. Every time you feel \"{fillers.get('top_filler', 'um')}\" "
                "coming, close your mouth and breathe instead. Replay and tally — aim to beat your count each round.",
                f"Under {max(1.0, round(fpm * 0.6, 1))} fillers per minute next session (now {fpm:.1f}).",
                _clamp01((fpm - 2) / 8), practice, 10))

    # ── Repetitions ──
    reps = [e for e in (stutter or {}).get("detected_events", []) if e.get("type") == "Repetition"]
    if len(reps) >= 2:
        words = ", ".join(f"“{e.get('word')} {e.get('word')}”" for e in reps[:4])
        out.append(Recommendation(
            "repetitions", "Smooth out restarts",
            f"{len(reps)} repeated words ({words}).",
            "Restarts break the flow of a sentence and draw attention away from the content.",
            "Before answering, decide your first five words. Practise starting 5 answers with them slowly "
            "(easy onset: start each sentence on a gentle breath out).",
            f"At most {max(0, len(reps) - 2)} repetitions next session (now {len(reps)}).",
            _clamp01(len(reps) / 8), "Conversation", 10))

    # ── Pronunciation ──
    if pronunciation and pronunciation.get("incorrect_words"):
        bad = [w.strip(".,!?\"'").lower() for w in pronunciation["incorrect_words"]]
        bad = list(dict.fromkeys(w for w in bad if len(w) > 2))[:6]
        score = pronunciation.get("score") or 0
        if bad and (score < 80 or len(bad) >= 3):
            out.append(Recommendation(
                "pronunciation", "Sharpen unclear words",
                f"These words were least clear: {', '.join(bad)} (pronunciation score {score:.0f}).",
                "Unclear key words force listeners to guess — accent is fine, clarity is what matters.",
                f"Say each word slowly three times, stressing the correct syllable, then use each in a sentence: "
                f"{', '.join(bad[:3])}. Record and compare with an online dictionary's audio.",
                "All of these words clear in a practice recording; pronunciation score above "
                f"{min(90, int(score) + 5)}.",
                _clamp01((85 - score) / 30 + len(bad) / 12), "Conversation", 10))

    # ── Eye contact ──
    if eye and eye.get("eye_contact_score") is not None:
        score = eye["eye_contact_score"]
        if score < 70:
            away = eye.get("look_away_percentage", 100 - score)
            direction = eye.get("dominant_gaze")
            reason = {
                "down": "mostly downwards — usually reading notes or the screen",
                "left": "mostly to the left, off-camera",
                "right": "mostly to the right, off-camera",
            }.get(direction, "away from the camera")
            trend = _trend("eye", score, prev_vision.get("eye_contact_score"), lower_is_better=False)
            out.append(Recommendation(
                "eye_contact", "Hold eye contact with the lens",
                f"You looked away {away:.0f}% of the time, {reason}.{trend}",
                "On video, the lens is your audience's eyes — looking away reads as unsure or disengaged.",
                "Put a small sticker beside your webcam. Practise a 2-minute answer looking at it; glance at notes "
                "only between sentences, never mid-sentence.",
                f"Eye contact above {min(85, int(score) + 15)}% next session (now {score:.0f}%).",
                _clamp01((75 - score) / 50), "Presentation", 10))

    # ── Posture ──
    if posture and posture.get("posture_score") is not None and posture["posture_score"] < 75:
        issues = []
        if posture.get("head_alignment", 100) < 70:
            issues.append(f"head tilted about {abs(posture.get('tilt_angle', 0)):.0f}°")
        if posture.get("shoulder_alignment", 100) < 70:
            issues.append("uneven shoulders")
        if posture.get("body_stability", 100) < 60:
            issues.append("frequent swaying")
        if issues:
            out.append(Recommendation(
                "posture", "Steady, upright posture",
                f"Posture score {posture['posture_score']:.0f}: {', '.join(issues)}.",
                "A level, still posture makes you look composed and lets your voice project.",
                "Before speaking: feet flat, shoulders back and level, chin parallel to the floor. Practise a "
                "1-minute answer with your hands resting still, then check the recording.",
                f"Posture above {min(85, int(posture['posture_score']) + 10)} next session.",
                _clamp01((80 - posture["posture_score"]) / 40), "Presentation", 5))

    # ── Facial tension ──
    if emotion and emotion.get("facial_tension", 0) >= 30:
        out.append(Recommendation(
            "expression", "Relax your expression",
            f"Your face looked tense for much of the session (tension {emotion['facial_tension']:.0f}/100; "
            f"most often {emotion.get('dominant_emotion', 'neutral')}).",
            "A relaxed face makes you look confident and approachable even when you feel nervous.",
            "Before starting: three slow breaths out through the mouth, relax your jaw, and smile at the first "
            "sentence. Practise opening lines with a deliberate, easy smile.",
            "Facial tension under 25 next session.",
            _clamp01((emotion["facial_tension"] - 20) / 50), practice, 5))

    # ── Monotone voice ──
    if prosody and prosody.get("pitch_variation_st") is not None and prosody["pitch_variation_st"] < 2.0:
        st = prosody["pitch_variation_st"]
        out.append(Recommendation(
            "vocal_variety", "Add more melody to your voice",
            f"Your pitch moved by only {st:.1f} semitones on average; 2–7 sounds lively.",
            "A flat voice makes even good content sound uninterested, and listeners stop paying attention.",
            "Read a short news paragraph three times: once flat, once exaggerated like a storyteller, then "
            "in between. Lift your pitch on the key word of every sentence and drop it at the full stop.",
            f"Vocal variety above {max(2.0, round(st + 0.7, 1))} semitones next session (now {st:.1f}).",
            _clamp01((2.2 - st) / 1.5), practice, 5))
    if prosody and prosody.get("loudness_dbfs") is not None and prosody["loudness_dbfs"] < -35:
        out.append(Recommendation(
            "volume", "Speak up",
            f"Your voice averaged {prosody['loudness_dbfs']:.0f} dBFS, which is quiet for a microphone recording.",
            "A quiet voice is hard to follow and can come across as unsure.",
            "Sit upright, breathe from your belly, and speak as if to someone at the back of a small room. "
            "Check that the mic level bar stays in the middle while you talk.",
            "Louder than −35 dBFS next session.",
            _clamp01((-35 - prosody["loudness_dbfs"]) / 12), practice, 5))

    # ── Hedging ──
    if language_use and language_use.get("hedges_per_100_words", 0) >= 2:
        h = language_use["hedges_per_100_words"]
        top = ", ".join(f"“{w}” ×{n}" for w, n in (language_use.get("top_hedges") or {}).items())
        out.append(Recommendation(
            "hedging", "State your points with confidence",
            f"{language_use['hedge_count']} hedging phrases ({h:.1f} per 100 words): {top}.",
            "Too many \"I think / maybe / kind of\" make your answers sound unsure even when you know them.",
            "Record a 1-minute answer, then write it down and delete every hedge. Say the cleaned-up version "
            "aloud twice: it should sound firmer, not ruder.",
            f"Under {max(1.0, round(h * 0.6, 1))} hedges per 100 words next session (now {h:.1f}).",
            _clamp01((h - 1) / 5), practice, 5))

    # ── Slow to respond ──
    if response_latency_sec is not None and response_latency_sec > 3:
        out.append(Recommendation(
            "response_time", "Start your answers sooner",
            f"You usually took {response_latency_sec:.1f} s to start answering after a question.",
            "Long silences before answering can read as unprepared; a short bridge buys thinking time.",
            "Practise opening with a bridge while you think: \"That's a good question. In my experience…\" "
            "Answer 5 random questions starting within 2 seconds.",
            "Start answering within 2 s next session.",
            _clamp01((response_latency_sec - 2) / 5), practice, 5))

    # ── Very short speaking time ──
    if duration_sec < 45:
        out.append(Recommendation(
            "length", "Speak in fuller answers",
            f"You spoke for only {duration_sec:.0f} s in total this session.",
            "Short turns give little chance to practise — and give the analysis little to measure.",
            "Use the 'point–reason–example' pattern: answer each question with one point, why, and a short example.",
            "Speak for at least 2 minutes in total next session.",
            0.35, practice, 10))

    out.sort(key=lambda r: -r.severity)
    return out


class _LLMItem(BaseModel):
    area: str
    title: str = Field(min_length=3, max_length=80)
    evidence: str = Field(min_length=10, max_length=400)
    why: str = Field(min_length=10, max_length=300)
    drill: str = Field(min_length=20, max_length=500)
    target: str = Field(min_length=5, max_length=200)


class _LLMPlan(BaseModel):
    summary: str = Field(min_length=10, max_length=500)
    focus: list[_LLMItem] = Field(min_length=1, max_length=MAX_ITEMS)


SYSTEM = """You are a speech coach writing a learner's improvement plan after a practice session.
Use ONLY the measured candidates you are given: choose at most 3 (most impactful for this learner's goal
and session type first), and for each keep its area exactly as given. Rewrite title/why/drill/target in
plain, encouraging, specific language for this learner. The evidence MUST keep the measured numbers and
moments. Each drill must be doable in 5–10 minutes and each target must be measurable.
Never mention an issue that is not in the candidates. Treat Malaysian accent as fine — focus on clarity.
Also write a 1–2 sentence summary that starts with something they did well (use the strengths given).
Return JSON only: {"summary": "...", "focus": [{"area", "title", "evidence", "why", "drill", "target"}]}"""


async def _llm_plan(candidates: list[Recommendation], context: dict) -> tuple[dict, list[Recommendation]] | None:
    client = get_llm_client()
    if client is None or not candidates:
        return None
    allowed = {c.area for c in candidates}
    payload = {
        **context,
        "candidates": [
            {k: v for k, v in asdict(c).items() if k in ("area", "title", "evidence", "why", "drill", "target")}
            for c in candidates[:6]
        ],
    }
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
    for _ in range(2):
        resp = await client.chat.completions.create(
            model=settings.llm_model, messages=messages, response_format={"type": "json_object"}, temperature=0.3
        )
        content = resp.choices[0].message.content or ""
        try:
            plan = _LLMPlan.model_validate(parse_json_object(content))
            unknown = [i.area for i in plan.focus if i.area not in allowed]
            if unknown:
                raise ValueError(f"areas not in the candidates: {unknown}; use only {sorted(allowed)}")
            by_area = {c.area: c for c in candidates}
            items = [
                Recommendation(
                    i.area, i.title, i.evidence, i.why, i.drill, i.target,
                    by_area[i.area].severity, by_area[i.area].practice_type, by_area[i.area].daily_minutes,
                )
                for i in plan.focus
            ]
            return {"summary": plan.summary}, items
        except (ValueError, ValidationError) as e:
            logger.warning("LLM coaching plan invalid, re-prompting: %s", e)
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"That was invalid: {e}. Return corrected JSON only."},
            ]
    return None


def _rule_summary(strengths: list[str], top: list[Recommendation]) -> str:
    good = f"Strongest today: {', '.join(strengths[:2])}. " if strengths else ""
    if not top:
        return good + "Nothing stood out as needing work in this session — keep practising at this level."
    return good + f"Biggest opportunity: {top[0].title.lower()} — {top[0].evidence}"


def _forecast(session_history_count: int) -> str:
    if session_history_count < 5:
        return "Practise the drills above for 10 minutes a day; most learners see clear gains on these exact numbers within 2 weeks."
    if session_history_count < 20:
        return "You're building a habit — keep the same focus for a week, then re-check these numbers."
    return "You have a long practice history: target one focus area per week and track it session to session."


def rule_based_plan(
    candidates: list[Recommendation], strengths: list[str], session_type: str, session_history_count: int,
    *, top: list[Recommendation] | None = None, summary: str | None = None, source: str = "rules",
) -> CoachingPlan:
    """The plan from measured candidates alone (also the shape the LLM-written plan is put into)."""
    top = candidates[:MAX_ITEMS] if top is None else top
    return CoachingPlan(
        exercises=[
            {
                "title": r.title, "area": r.area, "evidence": r.evidence, "why": r.why,
                "description": r.drill, "metric_target": r.target, "priority": r.priority,
                "practice_type": r.practice_type, "daily_minutes": r.daily_minutes,
            }
            for r in top
        ],
        summary=summary or _rule_summary(strengths, top),
        weekly_focus=top[0].title if top else "Keep your current level",
        daily_target_minutes=min(sum(r.daily_minutes for r in top), 30) if top else 10,
        next_session_type=top[0].practice_type if top else session_type,
        tips=[f"{r.title}: {r.target}" for r in top],
        progress_forecast=_forecast(session_history_count),
        source=source,
    )


async def build_plan(
    *,
    candidates: list[Recommendation],
    strengths: list[str],
    session_type: str,
    user_goal: str | None,
    session_history_count: int,
    transcript_excerpt: str | None,
    warnings: list[str],
) -> CoachingPlan:
    """The rule-based plan, re-chosen and re-worded for this learner by the LLM when one is configured."""
    try:
        result = await _llm_plan(candidates, {
            "session_type": session_type,
            "learner_goal": user_goal or "improve spoken communication",
            "strengths": strengths,
            "transcript_excerpt": (transcript_excerpt or "")[:800],
        })
        if result:
            meta, top = result
            return rule_based_plan(candidates, strengths, session_type, session_history_count,
                                   top=top, summary=meta["summary"], source="llm")
    except Exception as e:  # noqa: BLE001 — keep the measured plan
        logger.error("LLM coaching plan failed: %s", e)
        warnings.append(f"AI-written coaching plan failed ({e}); showing the measured plan.")
    return rule_based_plan(candidates, strengths, session_type, session_history_count)
