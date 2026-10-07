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
# "Confidence" can't be measured directly; what we can measure is how confident someone
# *comes across*, from cues listeners are known to react to: steady pace, few hesitations,
# repetitions and fillers, a quick start to answers, a relaxed face, an upright and steady
# posture, and looking at the camera. Each cue gets a 0-100 score from a plain rule (below),
# then a weighted average over the cues that were measured. The weights are a reasoned
# starting point, not fitted: calibrate them against human ratings (see docs/confidence-model.md).

CONFIDENCE_CUES = {
    # key: (label, channel, weight)
    "pace":        ("Speaking pace",               "voice", 0.10),
    "pauses":      ("Hesitation pauses",           "voice", 0.12),
    "repetitions": ("Word repetitions",            "voice", 0.08),
    "blocks":      ("Stutter blocks & stretches",  "voice", 0.07),
    "fillers":     ("Filler words",                "voice", 0.08),
    "response":    ("Time to start answering",     "voice", 0.05),
    "expression":  ("Confident expression",        "face",  0.10),
    "relaxed":     ("Relaxed face",                "face",  0.08),
    "posture":     ("Upright posture",             "body",  0.11),
    "stability":   ("Steady body",                 "body",  0.07),
    "eye_contact": ("Eye contact",                 "body",  0.14),
}


@dataclass
class ConfidenceResult:
    confidence_score: float
    speech_confidence: float | None   # voice cues
    facial_confidence: float | None   # expression + tension
    body_confidence: float | None     # posture, stability, eye contact
    label: str                        # High / Medium / Low
    coverage: float = 1.0             # share of the cue weight that was actually measured (0-1)
    cues: list[dict] | None = None    # [{key, label, channel, weight, value, score}] for the breakdown


def _pace_score(wpm: float) -> float:
    """120-160 wpm sounds natural; rushing or dragging both read as nerves."""
    return _clamp(100 - max(0.0, 120 - wpm, wpm - 160) * 1.5)


def confidence_cue_scores(
    *,
    speaking_rate: float | None = None,
    talk_minutes: float | None = None,
    pause_frequency: int | None = None,
    repetition_count: int | None = None,
    block_count: int | None = None,
    fillers_per_minute: float | None = None,
    response_latency_sec: float | None = None,
    emotion_confidence: float | None = None,
    facial_tension: float | None = None,
    posture_score: float | None = None,
    body_stability: float | None = None,
    eye_contact_score: float | None = None,
) -> dict[str, tuple[float, float]]:
    """{cue: (measured value, 0-100 score)} for every cue that has data. Counts become per-minute
    rates over the user's own talking time, so a long session isn't judged as less confident."""
    per_min = lambda n: n / talk_minutes if n is not None and talk_minutes and talk_minutes > 0.1 else None  # noqa: E731
    out: dict[str, tuple[float, float]] = {}
    if speaking_rate:
        out["pace"] = (speaking_rate, _pace_score(speaking_rate))
    if (r := per_min(pause_frequency)) is not None:
        out["pauses"] = (r, _clamp(100 - max(0.0, r - 20) * 4))       # 0.25 s+ pauses: ~15-20 a minute is normal speech
    if (r := per_min(repetition_count)) is not None:
        out["repetitions"] = (r, _clamp(100 - r * 15))               # "I I think": each one per minute costs 15
    if (r := per_min(block_count)) is not None:
        out["blocks"] = (r, _clamp(100 - r * 25))                    # 1.2-3 s silences mid-answer, stretched sounds
    if fillers_per_minute is not None:
        out["fillers"] = (fillers_per_minute, _clamp(100 - max(0.0, fillers_per_minute - 2) * 10))  # 1-2/min unnoticed
    if response_latency_sec is not None:
        out["response"] = (response_latency_sec, _clamp(100 - max(0.0, response_latency_sec - 1.5) * 12))
    if emotion_confidence is not None:
        out["expression"] = (emotion_confidence, _clamp(emotion_confidence))
    if facial_tension is not None:
        out["relaxed"] = (facial_tension, _clamp(100 - facial_tension))
    if posture_score is not None:
        out["posture"] = (posture_score, _clamp(posture_score))
    if body_stability is not None:
        out["stability"] = (body_stability, _clamp(body_stability))
    if eye_contact_score is not None:
        out["eye_contact"] = (eye_contact_score, _clamp(eye_contact_score))
    return out


MIN_CONFIDENCE_COVERAGE = 0.3  # below this share of the evidence, there's no honest confidence score


def estimate_confidence(**measured) -> ConfidenceResult | None:
    """Perceived confidence from up to 11 cues (CONFIDENCE_CUES); see confidence_cue_scores for inputs.
    None when under 30% of the cue weight was measured (e.g. only the response time)."""
    scored = confidence_cue_scores(**measured)
    total = sum(w for *_, w in CONFIDENCE_CUES.values())
    coverage = sum(CONFIDENCE_CUES[k][2] for k in scored) / total
    if coverage < MIN_CONFIDENCE_COVERAGE:
        return None

    def channel(name: str | None) -> float | None:
        return _weighted([(sc, CONFIDENCE_CUES[k][2]) for k, (_, sc) in scored.items()
                          if name is None or CONFIDENCE_CUES[k][1] == name])

    score = round(channel(None), 1)
    voice, face, body = channel("voice"), channel("face"), channel("body")
    return ConfidenceResult(
        confidence_score=score,
        speech_confidence=round(voice, 1) if voice is not None else None,
        facial_confidence=round(face, 1) if face is not None else None,
        body_confidence=round(body, 1) if body is not None else None,
        label="High" if score >= 75 else "Medium" if score >= 50 else "Low",
        coverage=round(coverage, 2),
        cues=[{"key": k, "label": CONFIDENCE_CUES[k][0], "channel": CONFIDENCE_CUES[k][1], "weight": CONFIDENCE_CUES[k][2],
               "value": round(v, 2), "score": round(sc, 1)} for k, (v, sc) in scored.items()],
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
