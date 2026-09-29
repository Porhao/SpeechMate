"""Cross-modal scoring for live sessions: confidence, the overall communication
score, and personalised practice recommendations.

Any input can be None (its model wasn't available). Weighted combinations are
renormalised over the inputs that exist, and recommendations only use metrics
that were actually measured.
"""

from dataclasses import asdict, dataclass, field


def _weighted(parts: list[tuple[float | None, float]]) -> float | None:
    present = [(v, w) for v, w in parts if v is not None]
    if not present:
        return None
    return sum(v * w for v, w in present) / sum(w for _, w in present)


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


# ── Confidence ──────────────────────────────────────────────────────────────

@dataclass
class ConfidenceResult:
    confidence_score: float
    speech_confidence: float | None   # pace, hesitations, fluency
    facial_confidence: float | None   # expression + facial tension
    body_confidence: float | None     # posture + stability
    label: str                        # High / Medium / Low


def estimate_confidence(
    *,
    speaking_rate: float | None,
    pause_frequency: int | None,
    fluency_score: float | None,
    emotion_confidence: float | None,
    facial_tension: float | None,
    posture_score: float | None,
    body_stability: float | None,
) -> ConfidenceResult | None:
    speech = None
    if speaking_rate is not None and fluency_score is not None:
        rate_score = max(0.0, 100 - abs(speaking_rate - 140) * 0.4)
        speech = _clamp((rate_score + fluency_score) / 2 - min((pause_frequency or 0) * 3, 30))
    facial = None
    if emotion_confidence is not None and facial_tension is not None:
        facial = _clamp((emotion_confidence + (100 - facial_tension)) / 2)
    body = None
    if posture_score is not None and body_stability is not None:
        body = _clamp((posture_score + body_stability) / 2)

    combined = _weighted([(speech, 0.40), (facial, 0.35), (body, 0.25)])
    if combined is None:
        return None
    score = round(combined, 1)
    return ConfidenceResult(
        confidence_score=score,
        speech_confidence=round(speech, 1) if speech is not None else None,
        facial_confidence=round(facial, 1) if facial is not None else None,
        body_confidence=round(body, 1) if body is not None else None,
        label="High" if score >= 75 else "Medium" if score >= 50 else "Low",
    )


# ── Overall communication score ─────────────────────────────────────────────

WEIGHTS = {"Fluency": 0.25, "Pronunciation": 0.25, "Confidence": 0.20, "Eye Contact": 0.15, "Posture": 0.15}


@dataclass
class CommunicationScore:
    overall_score: float | None
    grade: str | None
    strengths: list[str]
    improvement_areas: list[str]
    scored_on: list[str]        # which components were available


def compute_communication_score(scores: dict[str, float | None]) -> CommunicationScore:
    """`scores` keys are the WEIGHTS names (Fluency, Pronunciation, …)."""
    overall = _weighted([(scores.get(k), w) for k, w in WEIGHTS.items()])
    measured = {k: v for k, v in scores.items() if v is not None}
    if overall is None:
        return CommunicationScore(None, None, [], [], [])
    overall = round(overall, 1)
    return CommunicationScore(
        overall_score=overall,
        grade="Excellent" if overall >= 85 else "Good" if overall >= 70 else "Fair" if overall >= 55 else "Needs Work",
        strengths=[k for k, v in measured.items() if v >= 80],
        improvement_areas=[k for k, v in measured.items() if v < 65],
        scored_on=list(measured),
    )


# ── Recommendations ─────────────────────────────────────────────────────────

@dataclass
class Exercise:
    title: str
    description: str
    practice_type: str      # Conversation / Presentation / Pronunciation / Interview
    daily_minutes: int
    priority: str           # High / Medium / Low
    metric_target: str


@dataclass
class Recommendations:
    exercises: list[Exercise] = field(default_factory=list)
    weekly_focus: str = ""
    daily_target_minutes: int = 10
    next_session_type: str = "Conversation"
    tips: list[str] = field(default_factory=list)
    progress_forecast: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _below(v: float | None, limit: float) -> bool:
    return v is not None and v < limit


def generate_recommendations(
    *,
    fluency: float | None,
    pronunciation: float | None,
    eye_contact: float | None,
    confidence: float | None,
    posture: float | None,
    stuttering: float | None,
    filler_count: int | None,
    session_history_count: int,
) -> Recommendations:
    recs: list[Exercise] = []
    tips: list[str] = []

    if _below(fluency, 65):
        recs.append(Exercise(
            "Daily Fluency Drills",
            "Practice reading aloud for 10 minutes daily, focusing on smooth, continuous speech without stopping to self-correct.",
            "Conversation", 10, "High", "Fluency > 75%",
        ))
        tips.append("Try the 'smooth speech' technique: speak at 80% of your natural pace and focus on flow over perfection.")
    if stuttering is not None and stuttering > 20:
        recs.append(Exercise(
            "Stuttering Reduction Practice",
            "Use diaphragmatic breathing before speaking. Practice slow, deliberate speech with the AI conversation partner.",
            "Conversation", 15, "High", "Stuttering Score < 15%",
        ))
        tips.append("Before each session, take 3 deep breaths. Slow your speech — clarity beats speed.")
    if _below(pronunciation, 70):
        recs.append(Exercise(
            "Pronunciation Training",
            "Practice targeted word drills for your most common mispronunciations using the Pronunciation Training mode.",
            "Pronunciation", 10, "High" if pronunciation < 55 else "Medium", "Pronunciation > 80%",
        ))
    if filler_count is not None and filler_count > 10:
        recs.append(Exercise(
            "Filler Word Elimination",
            "Record yourself answering questions. When you feel the urge to say 'um' or 'uh', pause silently instead.",
            "Presentation", 10, "Medium", "< 5 fillers per minute",
        ))
        tips.append("Replace filler words with a confident pause — silence sounds more authoritative than 'um'.")
    if _below(eye_contact, 70):
        recs.append(Exercise(
            "Eye Contact Practice",
            "Practice presentation mode for 15 minutes daily. Look directly at the camera as if making eye contact with your audience.",
            "Presentation", 15, "High" if eye_contact < 55 else "Medium", "Eye Contact > 75%",
        ))
    if _below(confidence, 65):
        recs.append(Exercise(
            "Confidence Building Sessions",
            "Start with 2-minute storytelling sessions and gradually increase duration. Focus on posture and voice projection.",
            "Conversation", 10, "Medium", "Confidence > 70%",
        ))
        tips.append("Power posing for 2 minutes before speaking can measurably improve confidence.")
    if _below(posture, 75):
        recs.append(Exercise(
            "Presentation Posture Training",
            "Practice the 'triangle stance': feet shoulder-width apart, shoulders level, chin parallel to the floor.",
            "Presentation", 5, "Low", "Posture > 80%",
        ))

    if recs:
        top = sorted(recs, key=lambda r: {"High": 0, "Medium": 1, "Low": 2}[r.priority])[0]
        weekly_focus, next_session = top.title, top.practice_type
        minutes = min(sum(r.daily_minutes for r in recs[:3]), 30)
    else:
        weekly_focus, next_session, minutes = "Maintain your excellent communication skills", "Conversation", 10
        tips.append("You're performing excellently! Try a mock interview to challenge yourself further.")

    if session_history_count < 5:
        forecast = "With consistent daily practice, expect 10–15% improvement in your key metrics within 2 weeks."
    elif session_history_count < 20:
        forecast = "You're building strong habits. Continue at this pace for steady 5–8% weekly improvement."
    else:
        forecast = "Advanced practitioner level. Focus on fine-tuning specific weaknesses for peak performance."

    return Recommendations(recs, weekly_focus, minutes, next_session, tips, forecast)
