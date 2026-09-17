"""
Filler Word Detection Engine
Detects English and Bahasa Melayu filler words and communication habits.
"""
from dataclasses import dataclass, field
import re


# English fillers
EN_FILLERS = {
    "um", "uh", "like", "actually", "basically", "you know",
    "i mean", "kind of", "sort of", "literally", "right",
    "okay so", "so yeah", "well",
}

# Bahasa Melayu fillers
BM_FILLERS = {
    "err", "aa", "em", "kan", "lah", "mah", "weh",
    "erm", "macam", "tapi", "sebenarnya",
}

ALL_FILLERS = EN_FILLERS | BM_FILLERS


@dataclass
class FillerResult:
    total_fillers: int
    fillers_per_minute: float
    top_filler: str
    filler_breakdown: dict[str, int] = field(default_factory=dict)
    filler_positions: list[dict] = field(default_factory=list)  # [{word, position}]
    impact_level: str = "Low"   # Low / Medium / High


def detect_fillers(transcript: str, duration_seconds: float) -> FillerResult:
    text = transcript.lower()
    breakdown: dict[str, int] = {}

    for filler in ALL_FILLERS:
        # Match whole words only
        pattern = rf"\b{re.escape(filler)}\b"
        matches = re.findall(pattern, text)
        if matches:
            breakdown[filler] = len(matches)

    total = sum(breakdown.values())
    duration_min = max(duration_seconds / 60, 0.01)
    per_min = round(total / duration_min, 1)
    top = max(breakdown, key=breakdown.get) if breakdown else "none"

    # Build position list from word index
    words = text.split()
    positions = []
    for i, word in enumerate(words):
        if word in ALL_FILLERS:
            positions.append({"word": word, "position": i})

    if per_min < 3:
        impact = "Low"
    elif per_min < 7:
        impact = "Medium"
    else:
        impact = "High"

    return FillerResult(
        total_fillers=total,
        fillers_per_minute=per_min,
        top_filler=top,
        filler_breakdown=breakdown,
        filler_positions=positions,
        impact_level=impact,
    )
