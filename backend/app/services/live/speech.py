"""Speech delivery metrics for live sessions: fluency, filler words, stuttering.

Pauses come from ASR word timestamps when there are enough of them, and
otherwise from ffmpeg's silence detection on the real audio.
"""

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.services.live._ml import available

logger = logging.getLogger(__name__)

# ── Fluency ─────────────────────────────────────────────────────────────────

INTER_WORD_PAUSE_SEC = 0.25
EDGE_SEC = 0.5  # silence at the very start/end is getting ready, not a pause


@dataclass
class FluencyResult:
    fluency_score: float        # 0–100
    speaking_rate: float        # WPM over the whole recording
    articulation_rate: float    # WPM excluding pauses
    pause_frequency: int
    average_pause: float        # seconds
    longest_pause: float        # seconds
    speech_continuity: float    # 0–100
    grade: str                  # Excellent / Good / Fair / Needs Work
    pause_source: str           # word_timestamps | audio


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def grade(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Needs Work"


def inner_silences(silences: list[tuple[float, float]], duration: float) -> list[tuple[float, float]]:
    return [(s, e) for s, e in silences if s > EDGE_SEC and e < duration - EDGE_SEC]


def analyze_fluency(
    transcript: str,
    duration_sec: float,
    word_timestamps: list[dict],
    silences: list[tuple[float, float]],
) -> FluencyResult:
    """`silences` = ffmpeg silencedetect output (≥0.25 s), used when timestamps are too sparse."""
    word_count = _count_words(transcript)
    speaking_rate = round(word_count / max(duration_sec / 60, 0.01), 1)

    ts = word_timestamps
    if ts and len(ts) >= max(2, word_count * 0.5):
        pauses = [
            ts[i + 1]["start"] - ts[i]["end"]
            for i in range(len(ts) - 1)
            if ts[i + 1]["start"] - ts[i]["end"] > INTER_WORD_PAUSE_SEC
        ]
        speech_time = sum(w["end"] - w["start"] for w in ts)
        source = "word_timestamps"
    else:
        pauses = [e - s for s, e in inner_silences(silences, duration_sec)]
        speech_time = duration_sec - sum(pauses)
        source = "audio"

    articulation_rate = round(word_count / max(speech_time / 60, 0.01), 1)
    pause_frequency = len(pauses)

    # Penalise pace away from ~135 WPM and frequent pauses
    pace_score = 100 - abs(speaking_rate - 135) * 0.5
    raw = max(0.0, min(100.0, pace_score - min(pause_frequency * 2, 30)))

    return FluencyResult(
        fluency_score=round(raw, 1),
        speaking_rate=speaking_rate,
        articulation_rate=articulation_rate,
        pause_frequency=pause_frequency,
        average_pause=round(sum(pauses) / len(pauses), 2) if pauses else 0.0,
        longest_pause=round(max(pauses), 2) if pauses else 0.0,
        speech_continuity=round(max(0, 100 - pause_frequency * 3), 1),
        grade=grade(raw),
        pause_source=source,
    )


# ── Filler words (English + Bahasa Melayu) ──────────────────────────────────

# Always fillers: hesitation sounds
HESITATIONS = {"um", "umm", "uh", "uhh", "er", "err", "erm", "em", "aa", "ah", "hmm"}
# Fillers only when used as discourse markers: at the start of a clause or set off by a
# comma ("Like, I think…", "and, you know, it…"). "I like data", "what kind of tool",
# "tapi" (but) and Manglish particles (lah, kan: shown in the language card) are not fillers.
MARKERS = {
    "like", "you know", "i mean", "actually", "basically", "literally", "well", "right",
    "okay so", "so yeah", "macam", "sebenarnya",
}
ALL_FILLERS = HESITATIONS | MARKERS


def count_fillers(transcript: str) -> dict[str, int]:
    """Filler counts, most frequent first (see HESITATIONS / MARKERS)."""
    text = " " + re.sub(r"\s+", " ", transcript.lower().replace("’", "'")) + " "
    counts: dict[str, int] = {}
    for h in HESITATIONS:
        n = len(re.findall(rf"(?<![\w']){re.escape(h)}(?![\w'])", text))
        if n:
            counts[h] = n
    for m in sorted(MARKERS, key=len, reverse=True):
        # clause start (text start or after . , ! ? ;) or directly followed by a comma
        pattern = rf"(?:(?:^|[.,!?;]) ?{re.escape(m)}(?![\w']))|(?:(?<![\w']){re.escape(m)},)"
        n = len(re.findall(pattern, text.strip()))
        if n:
            counts[m] = n
            text = re.sub(rf"(?<![\w']){re.escape(m)}(?![\w'])", "#", text)  # don't recount inside longer phrases
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


@dataclass
class FillerResult:
    total_fillers: int
    fillers_per_minute: float
    top_filler: str
    filler_breakdown: dict[str, int] = field(default_factory=dict)
    impact_level: str = "Low"   # Low / Medium / High


def detect_fillers(transcript: str, duration_sec: float) -> FillerResult:
    breakdown = count_fillers(transcript)
    total = sum(breakdown.values())
    per_min = round(total / max(duration_sec / 60, 0.01), 1)
    return FillerResult(
        total_fillers=total,
        fillers_per_minute=per_min,
        top_filler=max(breakdown, key=breakdown.get) if breakdown else "none",
        filler_breakdown=breakdown,
        impact_level="Low" if per_min < 3 else "Medium" if per_min < 7 else "High",
    )


# ── Stuttering ──────────────────────────────────────────────────────────────
# A signal-processing heuristic over the real audio + transcript, not a trained
# classifier. A CNN+BiLSTM (Mel spectrogram → CNN → BiLSTM → attention →
# Fluent / Repetition / Prolongation / Block) trained on SEP-28k + UCLASS is
# the intended production component; it needs a labelled dataset and a
# training pipeline that don't exist in this repo yet.
#   Repetition   – consecutive identical words with a short gap between them
#   Block        – mid-utterance silence ≥ 1.2 s (ffmpeg silence detection)
#   Prolongation – sustained, steady-energy voiced segment (needs librosa)

BLOCK_MIN_SECONDS = 1.2
PROLONGATION_MIN_SECONDS = 0.35
REPETITION_MAX_GAP = 0.6


@dataclass
class StutteringResult:
    stuttering_score: float     # 0–100, higher = more stuttering
    severity: str               # None / Mild / Moderate / Severe
    repetition_count: int
    prolongation_count: int
    block_count: int
    detected_events: list[dict]  # [{type, start_time, end_time, word}]
    method: str


def _severity(score: float) -> str:
    return "None" if score == 0 else "Mild" if score < 25 else "Moderate" if score < 50 else "Severe"


def _prolongations(wav_16k: Path) -> list[dict]:
    import librosa
    import numpy as np

    from app.services.live.audio import MODEL_SAMPLE_RATE, load_wav_float

    y = load_wav_float(wav_16k)
    if y.size == 0:
        return []
    hop = 256
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
    zcr = librosa.feature.zero_crossing_rate(y, frame_length=1024, hop_length=hop)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=MODEL_SAMPLE_RATE, hop_length=hop)
    voiced = (rms > np.percentile(rms, 40)) & (zcr < np.percentile(zcr, 60))

    events, run_start = [], None
    for i, is_voiced in enumerate(voiced):
        if is_voiced and run_start is None:
            run_start = i
        elif not is_voiced and run_start is not None:
            segment = rms[run_start:i]
            stability = 1 - segment.std() / (segment.mean() + 1e-6)
            if times[i - 1] - times[run_start] >= PROLONGATION_MIN_SECONDS and stability > 0.6:
                events.append({
                    "type": "Prolongation",
                    "start_time": round(float(times[run_start]), 2),
                    "end_time": round(float(times[i - 1]), 2),
                    "word": "",
                })
            run_start = None
    return events


def detect_stuttering(
    transcript: str,
    word_timestamps: list[dict],
    silences: list[tuple[float, float]],
    duration_sec: float,
    wav_16k: Path,
) -> StutteringResult:
    events: list[dict] = []

    words = transcript.lower().split()
    ts = word_timestamps if len(word_timestamps) == len(words) else []
    for i in range(len(words) - 1):
        if words[i].strip(".,!?") != words[i + 1].strip(".,!?"):
            continue
        if ts and ts[i + 1]["start"] - ts[i]["end"] > REPETITION_MAX_GAP:
            continue  # a new sentence that happens to start with the same word
        events.append({
            "type": "Repetition",
            "start_time": round(ts[i]["start"], 2) if ts else None,
            "end_time": round(ts[i + 1]["end"], 2) if ts else None,
            "word": words[i].strip(".,!?"),
        })

    for s, e in inner_silences(silences, duration_sec):
        if e - s >= BLOCK_MIN_SECONDS:
            events.append({"type": "Block", "start_time": round(s, 2), "end_time": round(e, 2), "word": ""})

    method = "transcript + audio silence"
    if available("librosa", "numpy"):
        try:
            events += _prolongations(wav_16k)
            method = "transcript + audio silence + energy (librosa)"
        except Exception:  # noqa: BLE001
            logger.exception("Prolongation detection failed")
    else:
        # Transcript-only hint: ASR sometimes spells prolonged sounds out ("sooo")
        for m in re.finditer(r"\b\w*(\w)\1{2,}\w*\b", transcript.lower()):
            events.append({"type": "Prolongation", "start_time": None, "end_time": None, "word": m.group(0)})

    counts = {t: sum(1 for ev in events if ev["type"] == t) for t in ("Repetition", "Prolongation", "Block")}
    score = float(min(sum(counts.values()) * 8, 100))
    return StutteringResult(
        stuttering_score=score,
        severity=_severity(score),
        repetition_count=counts["Repetition"],
        prolongation_count=counts["Prolongation"],
        block_count=counts["Block"],
        detected_events=sorted(events, key=lambda ev: ev["start_time"] if ev["start_time"] is not None else -1),
        method=method,
    )


def to_dict(result) -> dict:
    return asdict(result)
