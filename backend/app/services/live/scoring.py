"""Cross-modal scoring for live sessions: confidence and the overall communication
score (recommendations are in coaching.py).

Any input can be None (its model wasn't available). Weighted combinations are
renormalised over the inputs that exist, and recommendations only use metrics
that were actually measured.
"""

from dataclasses import dataclass


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
