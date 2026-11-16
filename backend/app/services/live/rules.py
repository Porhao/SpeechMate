"""Every metric's comfortable range and its 0–100 score, in one place. The confidence cues (scoring.py),
the pillars (extra_metrics.py), fluency (speech.py) and the coaching triggers (coaching.py) all read
these, so a recalibration is one edit. The Reference page (frontend/app/(app)/methodology/page.tsx)
states the same numbers for users."""

STRONG, OKAY = 75, 55  # status bands for any 0–100 score: good / ok / work


def clamp(v: float) -> float:
    return round(max(0.0, min(100.0, v)), 1)


def status(score: float | None) -> str | None:
    if score is None:
        return None
    return "good" if score >= STRONG else "ok" if score >= OKAY else "work"


PACE_WPM = (120, 160)          # easy to follow; slower drags, faster rushes


def pace_score(wpm: float) -> float:
    lo, hi = PACE_WPM
    return clamp(100 - max(0.0, lo - wpm, wpm - hi) * 2.5)


FILLERS_OK_PER_MIN = 2         # one or two a minute go unnoticed


def filler_score(per_min: float) -> float:
    return clamp(100 - max(0.0, per_min - FILLERS_OK_PER_MIN) * 12)


RESPONSE_OK_SEC = 1.5          # end of the question → first sound


def latency_score(sec: float) -> float:
    return clamp(100 - max(0.0, sec - RESPONSE_OK_SEC) * 12)


PITCH_ST = (2.0, 7.0)          # pitch movement in semitones: under 2 sounds monotone, over 7 erratic


def pitch_score(st: float) -> float:
    lo, hi = PITCH_ST
    if st < lo:
        return clamp(40 + (st / lo) * 50)
    return clamp(100 - max(0.0, st - hi) * 8)


QUIET_DBFS, STEADY_DB = -35, 7  # quieter than −35 dBFS is hard to hear; ±7 dB = steady


def loudness_score(mean_db: float, var_db: float) -> float:
    level = 100 - max(0.0, QUIET_DBFS - mean_db) * 4
    steadiness = 100 - max(0.0, var_db - STEADY_DB) * 8
    return clamp(min(level, steadiness))


def richness_score(mattr: float) -> float:
    return clamp((mattr - 0.45) / 0.27 * 100)


HEDGES_OK_PER_100 = 1


def hedge_score(per_100: float) -> float:
    return clamp(100 - max(0.0, per_100 - HEDGES_OK_PER_100) * 18)


GESTURE_SHARE = (0.2, 0.6)     # share of the time hands are visible and moving


def gesture_score(ratio: float) -> float:
    lo, hi = GESTURE_SHARE
    # Hands out of view is common at a desk: it caps the score, it isn't "bad"
    return clamp(60 + min(1.0, ratio / lo) * 40 - max(0.0, ratio - hi) * 60)


EYE_CONTACT_OK = 70            # % of the time looking at the lens
TENSION_OK = 30                # facial tension (share of fearful / angry / sad)
POSTURE_OK = 75

# Posture problems vision.py measures and coaching.py words
IN_FRAME_MIN_PCT = 80          # shoulders in view at least this share of the time
POSTURE_ISSUE_PCT = 20         # slumped, or filmed from below, for this share of the time or more
ALIGNMENT_MIN = 70             # head and shoulder alignment
STABILITY_MIN = 60             # torso steadiness
