"""
Fluency Assessment Engine
Analyses WPM, pause frequency, speech continuity, and articulation rate.
"""
import re
from dataclasses import dataclass
from .asr import ASRResult


@dataclass
class FluencyResult:
    fluency_score: float        # 0–100
    speaking_rate: float        # WPM
    articulation_rate: float    # WPM excluding pauses
    pause_frequency: int        # pause count
    average_pause: float        # seconds
    longest_pause: float        # seconds
    speech_continuity: float    # 0–100
    grade: str                  # Excellent / Good / Fair / Needs Work


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def analyze_fluency(asr: ASRResult) -> FluencyResult:
    """
    Uses ASR word_timestamps (when available — real faster-whisper output) to
    compute actual inter-word pauses and articulation rate. Falls back to a
    duration/word-count estimate when timestamps are too sparse (e.g. the
    stub ASR result, which only carries a handful of sample timestamps).
    """
    word_count = _count_words(asr.transcript)
    duration_min = max(asr.duration_seconds / 60, 0.01)
    speaking_rate = round(word_count / duration_min, 1)

    ts = asr.word_timestamps
    if ts and len(ts) >= max(2, word_count * 0.5):
        pauses = [
            ts[i + 1]["start"] - ts[i]["end"]
            for i in range(len(ts) - 1)
            if ts[i + 1]["start"] - ts[i]["end"] > 0.25
        ]
        pause_frequency = len(pauses)
        average_pause = round(sum(pauses) / len(pauses), 2) if pauses else 0.0
        longest_pause = round(max(pauses), 2) if pauses else 0.0
        speech_time = sum(w["end"] - w["start"] for w in ts)
        articulation_rate = round(word_count / max(speech_time / 60, 0.01), 1)
    else:
        pause_frequency = max(0, int(word_count * 0.06))
        average_pause = 0.9
        longest_pause = 2.1
        articulation_rate = round(speaking_rate * 1.1, 1)

    # Score: penalise for pace outside 110–160 WPM and high pause frequency
    pace_score = 100 - abs(speaking_rate - 135) * 0.5
    pause_penalty = min(pause_frequency * 2, 30)
    raw = max(0, min(100, pace_score - pause_penalty))

    continuity = max(0, 100 - pause_frequency * 3)

    if raw >= 80:
        grade = "Excellent"
    elif raw >= 65:
        grade = "Good"
    elif raw >= 50:
        grade = "Fair"
    else:
        grade = "Needs Work"

    return FluencyResult(
        fluency_score=round(raw, 1),
        speaking_rate=speaking_rate,
        articulation_rate=articulation_rate,
        pause_frequency=pause_frequency,
        average_pause=average_pause,
        longest_pause=longest_pause,
        speech_continuity=round(continuity, 1),
        grade=grade,
    )
