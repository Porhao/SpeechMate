"""
Confidence Estimation Engine
Combines speech features, facial features, and body language signals.
"""
from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    confidence_score: float     # 0–100
    speech_confidence: float    # derived from pace, hesitations, volume stability
    facial_confidence: float    # derived from emotion + facial tension
    body_confidence: float      # derived from posture + movement
    label: str                  # High / Medium / Low


def estimate_confidence(
    speaking_rate: float,           # WPM
    pause_frequency: int,
    fluency_score: float,
    emotion_confidence: float,      # from FER model
    facial_tension: float,          # 0–100, lower = more relaxed
    posture_score: float,
    body_stability: float,
) -> ConfidenceResult:
    # Speech confidence: reward good WPM, penalise high pauses and low fluency
    rate_score = max(0, 100 - abs(speaking_rate - 140) * 0.4)
    pause_penalty = min(pause_frequency * 3, 30)
    speech_confidence = max(0, min(100, (rate_score + fluency_score) / 2 - pause_penalty))

    # Facial confidence: from FER emotion output and facial tension
    facial_confidence = max(0, min(100, (emotion_confidence + (100 - facial_tension)) / 2))

    # Body confidence: from posture and stability
    body_confidence = max(0, min(100, (posture_score + body_stability) / 2))

    # Weighted combination per the spec formula
    combined = (
        speech_confidence * 0.40
        + facial_confidence * 0.35
        + body_confidence * 0.25
    )
    score = round(combined, 1)

    if score >= 75:
        label = "High"
    elif score >= 50:
        label = "Medium"
    else:
        label = "Low"

    return ConfidenceResult(
        confidence_score=score,
        speech_confidence=round(speech_confidence, 1),
        facial_confidence=round(facial_confidence, 1),
        body_confidence=round(body_confidence, 1),
        label=label,
    )
