"""
Communication Effectiveness Scoring
Combines speech + vision signals into a single weighted score.
Formula: weighted average of Fluency, Pronunciation, Confidence, Eye Contact, Posture
"""
from dataclasses import dataclass


WEIGHTS = {
    "fluency":       0.25,
    "pronunciation": 0.25,
    "confidence":    0.20,
    "eye_contact":   0.15,
    "posture":       0.15,
}


@dataclass
class CommunicationScore:
    overall_score: float
    fluency_score: float
    pronunciation_score: float
    confidence_score: float
    eye_contact_score: float
    posture_score: float
    grade: str
    strengths: list[str]
    improvement_areas: list[str]


def compute_communication_score(
    fluency: float,
    pronunciation: float,
    confidence: float,
    eye_contact: float,
    posture: float,
) -> CommunicationScore:
    overall = round(
        fluency * WEIGHTS["fluency"]
        + pronunciation * WEIGHTS["pronunciation"]
        + confidence * WEIGHTS["confidence"]
        + eye_contact * WEIGHTS["eye_contact"]
        + posture * WEIGHTS["posture"],
        1,
    )

    scores = {
        "Fluency": fluency,
        "Pronunciation": pronunciation,
        "Confidence": confidence,
        "Eye Contact": eye_contact,
        "Posture": posture,
    }
    strengths = [k for k, v in scores.items() if v >= 80]
    improvements = [k for k, v in scores.items() if v < 65]

    if overall >= 85:
        grade = "Excellent"
    elif overall >= 70:
        grade = "Good"
    elif overall >= 55:
        grade = "Fair"
    else:
        grade = "Needs Work"

    return CommunicationScore(
        overall_score=overall,
        fluency_score=fluency,
        pronunciation_score=pronunciation,
        confidence_score=confidence,
        eye_contact_score=eye_contact,
        posture_score=posture,
        grade=grade,
        strengths=strengths,
        improvement_areas=improvements,
    )
