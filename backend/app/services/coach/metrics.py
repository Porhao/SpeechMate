"""Deterministic delivery metrics (Coach Agent Stage 1, Path B).

Pure functions, no LLM: pace, pauses, filler words and how much of the
ideal script's key content the speaker covered. The LLM only turns these
numbers into feedback, so "why did the coach say X?" is always traceable.
"""

import re
from collections import Counter

# Multi-word fillers first so "you know" isn't also counted as nothing

STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have
having he her here hers herself him himself his how i if in into is it its itself just let lets me
more most my myself no nor not now of off on once only or other our ours ourselves out over own same
she should so some such than that the their theirs them themselves then there these they this those
through to too under until up very was we were what when where which while who whom why will with
would you your yours yourself yourselves today also well really thing things going get got one two
three first next let's we're it's that's there's here's you're i'm don't can't
""".split())

# Pauses at the very start/end of a recording are just the user getting ready
EDGE_TOLERANCE_SEC = 0.3
LONG_PAUSE_SEC = 2.0


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))


def count_fillers(transcript: str) -> dict[str, int]:
    """Same rules as live sessions: hesitations always, discourse markers only in context."""
    from app.services.live.speech import count_fillers as _count

    return _count(transcript)


def key_terms(text: str, limit: int = 25) -> list[str]:
    """Most frequent content words of a script, in order of importance."""
    words = [w.strip("'") for w in _words(text)]
    content = [w for w in words if len(w) > 3 and w not in STOPWORDS and not w.isdigit()]
    return [w for w, _ in Counter(content).most_common(limit)]


def script_coverage(transcript: str, ideal_text: str) -> tuple[float | None, list[str]]:
    """Share of the ideal script's key terms the speaker used, plus the missed ones."""
    terms = key_terms(ideal_text)
    if not terms:
        return None, []
    spoken = {w.strip("'") for w in _words(transcript)}
    # Light stemming so "benefit" matches "benefits"
    spoken |= {w.rstrip("s") for w in spoken}
    missed = [t for t in terms if t not in spoken and t.rstrip("s") not in spoken]
    return round(1 - len(missed) / len(terms), 3), missed[:8]


def slide_coverage(transcript: str, slides: list[tuple[int, str, str | None]]) -> list[dict]:
    """Per slide: how much of its key point and script terms the speaker covered.
    `slides` = [(slide_index, script_text, key_point from the deck insights)]."""
    out = []
    for index, script, key_point in slides:
        coverage, missed = script_coverage(transcript, f"{key_point or ''} {key_point or ''} {script}")
        if coverage is None:
            continue
        out.append({"slide_index": index, "key_point": key_point, "coverage": coverage, "missed": missed[:5],
                    "status": "covered" if coverage >= 0.6 else "partly" if coverage >= 0.3 else "missed"})
    return out


def compute_metrics(
    *,
    duration_sec: float,
    silences: list[tuple[float, float]],
    transcript: str | None,
    ideal_text: str,
    ideal_duration_sec: float | None,
    slides: list[tuple[int, str, str | None]] | None = None,
) -> dict:
    """Build the metrics dict stored on the practice session."""
    inner_pauses = [
        (start, end)
        for start, end in silences
        if start > EDGE_TOLERANCE_SEC and end < duration_sec - EDGE_TOLERANCE_SEC
    ]
    pause_lengths = [end - start for start, end in inner_pauses]
    long_pauses = sorted(
        ({"at_sec": round(s, 1), "duration_sec": round(e - s, 1)} for s, e in inner_pauses if e - s >= LONG_PAUSE_SEC),
        key=lambda p: -p["duration_sec"],
    )[:5]

    ideal_words = len(_words(ideal_text))
    ideal_wpm = round(ideal_words / ideal_duration_sec * 60, 1) if ideal_duration_sec else None

    metrics: dict = {
        "duration_sec": round(duration_sec, 1),
        "ideal_duration_sec": round(ideal_duration_sec, 1) if ideal_duration_sec else None,
        "duration_ratio": round(duration_sec / ideal_duration_sec, 2) if ideal_duration_sec else None,
        "pause_count": len(inner_pauses),
        "total_pause_sec": round(sum(pause_lengths), 1),
        "longest_pause_sec": round(max(pause_lengths), 1) if pause_lengths else 0.0,
        "long_pauses": long_pauses,
        "ideal_wpm": ideal_wpm,
        "has_transcript": transcript is not None,
    }

    if transcript is not None:
        word_count = len(_words(transcript))
        fillers = count_fillers(transcript)
        filler_total = sum(fillers.values())
        coverage, missed = script_coverage(transcript, ideal_text)
        metrics.update({
            "word_count": word_count,
            "wpm": round(word_count / duration_sec * 60, 1) if duration_sec > 0 else None,
            "filler_word_count": filler_total,
            "filler_words": fillers,
            "fillers_per_minute": round(filler_total / duration_sec * 60, 1) if duration_sec > 0 else None,
            "script_coverage": coverage,
            "missed_key_terms": missed,
        })
        if slides and len(slides) > 1:
            metrics["slide_coverage"] = slide_coverage(transcript, slides)
    return metrics
