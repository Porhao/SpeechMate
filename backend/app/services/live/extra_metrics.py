"""Extra live-session metrics, and the four simple "pillars" the results page shows.

- Voice: vocal variety (pitch movement in semitones) and loudness / steadiness (dBFS).
- Language: vocabulary richness (moving-average type-token ratio) and hedging phrases.
- Visual: gestures (hands visible and moving) and head stability (MediaPipe Pose).
- Conversation: response time (measured in the browser from the end of the AI's turn
  to the start of yours) and Gaze Tunneling (also from the browser).

Pillars group every measured metric into four 0–100 scores so the analysis reads
simply: Voice & delivery · Language & clarity · Body language · Confidence & presence.
Each metric carries its value, a 0–100 score, a status and the comfortable range.
"""

import logging
import math
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

HEDGES = (
    "i think", "i guess", "maybe", "kind of", "kinda", "sort of", "probably", "perhaps", "i'm not sure",
    "i am not sure", "i don't know", "i suppose", "possibly", "a bit", "somewhat", "rasa macam", "mungkin",
)
MATTR_WINDOW = 50


def _clamp(v: float) -> float:
    return round(max(0.0, min(100.0, v)), 1)


def _status(score: float | None) -> str | None:
    if score is None:
        return None
    return "good" if score >= 75 else "ok" if score >= 55 else "work"


# ── Voice: pitch and loudness ───────────────────────────────────────────────

@dataclass
class ProsodyResult:
    pitch_mean_hz: float
    pitch_variation_st: float     # std of pitch in semitones; < 1.5 sounds monotone
    loudness_dbfs: float          # mean level of voiced frames
    loudness_variation_db: float  # std of voiced-frame level; large = fading in and out
    voiced_ratio: float           # share of frames with voice


def analyze_prosody(wav_16k: Path) -> ProsodyResult | None:
    """Pitch with librosa's YIN over voiced frames; loudness from frame RMS."""
    import librosa
    import numpy as np

    from app.services.live.audio import MODEL_SAMPLE_RATE, load_wav_float

    y = load_wav_float(wav_16k)
    if y.size < MODEL_SAMPLE_RATE:
        return None
    hop = 320  # 20 ms
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
    db = 20 * np.log10(rms + 1e-9)
    voiced = db > max(np.percentile(db, 30), -50)
    if voiced.sum() < 25:
        return None
    f0 = librosa.yin(y, fmin=70, fmax=400, sr=MODEL_SAMPLE_RATE, frame_length=1024, hop_length=hop)
    n = min(len(f0), len(voiced))
    f0v = f0[:n][voiced[:n]]
    f0v = f0v[(f0v > 75) & (f0v < 390)]
    if f0v.size < 25:
        return None
    semitones = 12 * np.log2(f0v / np.median(f0v))
    # Trim octave errors before measuring spread
    semitones = semitones[np.abs(semitones) < 12]
    return ProsodyResult(
        pitch_mean_hz=round(float(np.median(f0v)), 1),
        pitch_variation_st=round(float(np.std(semitones)), 2),
        loudness_dbfs=round(float(np.mean(db[voiced])), 1),
        loudness_variation_db=round(float(np.std(db[voiced])), 1),
        voiced_ratio=round(float(voiced.mean()), 2),
    )


# ── Language ────────────────────────────────────────────────────────────────

@dataclass
class LanguageUseResult:
    word_count: int
    vocabulary_richness: float | None   # MATTR 0–1
    unique_words: int
    hedge_count: int
    hedges_per_100_words: float
    top_hedges: dict[str, int]
    avg_sentence_words: float | None


def analyze_language_use(transcript: str) -> LanguageUseResult | None:
    words = re.findall(r"[a-zA-Z']+", transcript.lower())
    if len(words) < 10:
        return None
    if len(words) >= MATTR_WINDOW:
        ratios = [len(set(words[i:i + MATTR_WINDOW])) / MATTR_WINDOW for i in range(len(words) - MATTR_WINDOW + 1)]
        mattr = statistics.mean(ratios)
    else:
        mattr = len(set(words)) / len(words)
    text = " " + " ".join(words) + " "
    hedges = {h: text.count(f" {h} ") for h in HEDGES}
    hedges = {h: n for h, n in sorted(hedges.items(), key=lambda kv: -kv[1]) if n}
    total = sum(hedges.values())
    sentences = [s for s in re.split(r"[.!?]+", transcript) if s.strip()]
    return LanguageUseResult(
        word_count=len(words),
        vocabulary_richness=round(mattr, 3),
        unique_words=len(set(words)),
        hedge_count=total,
        hedges_per_100_words=round(total / len(words) * 100, 1),
        top_hedges=dict(list(hedges.items())[:4]),
        avg_sentence_words=round(len(words) / len(sentences), 1) if len(sentences) > 1 else None,
    )


# ── Visual: gestures and head stability ─────────────────────────────────────

NOSE, LEFT_WRIST, RIGHT_WRIST, LEFT_SHOULDER, RIGHT_SHOULDER = 0, 15, 16, 11, 12


@dataclass
class GestureResult:
    hands_visible_ratio: float     # share of frames with at least one hand in view
    gesture_ratio: float           # share of frames where a visible hand moved noticeably
    head_stability: float          # 0–100 (nose movement relative to the shoulders)
    frame_count: int


def analyze_gestures(frames: list) -> GestureResult | None:
    from app.services.live.vision import _pose

    visible, moving, heads = 0, 0, []
    prev_wrists = None
    used = 0
    for frame in frames:
        result = _pose().process(frame)
        if not result.pose_landmarks:
            prev_wrists = None
            continue
        lm = result.pose_landmarks.landmark
        used += 1
        width = abs(lm[LEFT_SHOULDER].x - lm[RIGHT_SHOULDER].x) or 0.2
        mid_x = (lm[LEFT_SHOULDER].x + lm[RIGHT_SHOULDER].x) / 2
        mid_y = (lm[LEFT_SHOULDER].y + lm[RIGHT_SHOULDER].y) / 2
        heads.append(((lm[NOSE].x - mid_x) / width, (lm[NOSE].y - mid_y) / width))
        wrists = [(lm[i].x, lm[i].y) for i in (LEFT_WRIST, RIGHT_WRIST) if lm[i].visibility > 0.5 and lm[i].y < 1.0]
        if wrists:
            visible += 1
            if prev_wrists:
                shift = max(math.dist(a, b) for a in wrists for b in prev_wrists) / width
                if shift > 0.15:
                    moving += 1
        prev_wrists = wrists or None
    if used < 3:
        return None
    hx = statistics.pstdev(h[0] for h in heads)
    hy = statistics.pstdev(h[1] for h in heads)
    return GestureResult(
        hands_visible_ratio=round(visible / used, 2),
        gesture_ratio=round(moving / used, 2),
        head_stability=_clamp(100 - (hx + hy) * 250),
        frame_count=used,
    )


# ── Scores for each metric ──────────────────────────────────────────────────

def pace_score(wpm: float) -> float:
    return _clamp(100 - max(0.0, 120 - wpm, wpm - 160) * 2.5)


def filler_score(per_min: float) -> float:
    return _clamp(100 - max(0.0, per_min - 2) * 12)


def pitch_score(st: float) -> float:
    if st < 2.0:
        return _clamp(40 + (st / 2.0) * 50)
    return _clamp(100 - max(0.0, st - 7) * 8)


def loudness_score(mean_db: float, var_db: float) -> float:
    level = 100 - max(0.0, -35 - mean_db) * 4   # quieter than −35 dBFS is hard to hear
    steadiness = 100 - max(0.0, var_db - 7) * 8
    return _clamp(min(level, steadiness))


def richness_score(mattr: float) -> float:
    return _clamp((mattr - 0.45) / 0.27 * 100)


def hedge_score(per_100: float) -> float:
    return _clamp(100 - max(0.0, per_100 - 1) * 18)


def latency_score(sec: float) -> float:
    return _clamp(100 - max(0.0, sec - 1.5) * 12)


def gesture_score(g: GestureResult) -> float:
    # Hands out of view is common at a desk — it caps the score, it isn't "bad"
    return _clamp(60 + min(1.0, g.gesture_ratio / 0.2) * 40 - max(0.0, g.gesture_ratio - 0.6) * 60)


def _metric(key, label, value, display, score, good_range, unit_hint=""):
    return {"key": key, "label": label, "value": value, "display": display, "score": score,
            "status": _status(score), "range": good_range, "hint": unit_hint}


# ── Gaze Tunneling ──────────────────────────────────────────────────────────
# Do you look away when you stumble? Pearson r between the share of each 5 s window spent
# looking away and the number of disfluencies in it, computed from the recording itself:
# word timings from speech recognition and a gaze sample every ~0.5 s from the video, so
# both sit on one timeline (the earlier browser version stamped each stumble when its
# transcript arrived, seconds late). Significance by circular shift: r is recomputed with
# the disfluency series rotated against the gaze series by every possible offset, which
# keeps both series' own clustering; p = share of offsets that match or beat the real r.

GT_WINDOW_SEC = 5.0
# The smallest possible p is 1/windows, so under 20 windows (100 s of the user's speech) no
# link could ever reach p < 0.05: the metric is left out rather than shown undecidable.
GT_MIN_WINDOWS, GT_MIN_EVENTS = 20, 3


def disfluency_events(words: list[dict], stutter_events: list[dict]) -> list[dict]:
    """[{type: filler|repetition|block|prolongation, t_sec, word}] in time order: hesitations (um, uh…)
    at their word timings, and the disfluency detector's timed events."""
    from app.services.live.speech import HESITATIONS

    out = [{"type": "filler", "t_sec": round(w["start"], 2), "word": w["word"]} for w in words or []
           if re.sub(r"[^\w']", "", w.get("word", "").lower()) in HESITATIONS]
    out += [{"type": e["type"].lower(), "t_sec": e["start_time"], "word": e.get("word", "")}
            for e in stutter_events or [] if e.get("start_time") is not None]
    return sorted(out, key=lambda e: e["t_sec"])


def disfluency_times(words: list[dict], stutter_events: list[dict]) -> list[float]:
    """Seconds at which the speaker hesitated (um, uh…), repeated a word, blocked or prolonged a sound."""
    return [e["t_sec"] for e in disfluency_events(words, stutter_events)]


def _pearson(x: list[float], y: list[float]) -> float | None:
    mx, my = statistics.mean(x), statistics.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx > 0 and sy > 0 else None


def gaze_tunneling(gaze: list[tuple[float, bool]], events: list[float], duration_sec: float) -> dict | None:
    """{r, p, label, windows, events} or None when there is too little to judge (under 100 s,
    under 3 disfluencies, gaze missing in most windows, or no variation)."""
    n = max(1, math.ceil(duration_sec / GT_WINDOW_SEC))
    if n < GT_MIN_WINDOWS or len(events) < GT_MIN_EVENTS:
        return None
    away = [[] for _ in range(n)]
    for t, a in gaze:
        away[min(int(t // GT_WINDOW_SEC), n - 1)].append(a)
    seen = [w for w in away if w]
    if len(seen) < n / 2:
        return None
    fill = statistics.mean(sum(w) / len(w) for w in seen)
    x = [sum(w) / len(w) if w else fill for w in away]       # share of the window looking away
    y = [0.0] * n
    for t in events:
        y[min(int(t // GT_WINDOW_SEC), n - 1)] += 1
    r = _pearson(x, y)
    if r is None:
        return None
    shifted = [_pearson(x, y[k:] + y[:k]) for k in range(1, n)]
    p = (1 + sum(1 for v in shifted if v is not None and v >= r)) / n
    label = ("Strong link" if r > 0.4 else "Some link") if p < 0.05 and r > 0.15 else "No clear link"
    return {"r": round(r, 2), "p": round(p, 3), "label": label, "windows": n, "events": len(events)}


def median_latency(client_metrics: dict | None) -> float | None:
    vals = [v for v in (client_metrics or {}).get("response_latency_sec") or [] if isinstance(v, (int, float)) and 0 <= v < 60]
    return round(statistics.median(vals), 2) if vals else None


def build_pillars(analysis: dict, prosody: ProsodyResult | None, lang_use: LanguageUseResult | None,
                  gestures: GestureResult | None, client_metrics: dict | None, tunneling: dict | None = None) -> dict:
    """The four pillars, each {score, status, metrics:[...]} — only measured metrics are listed."""
    sp, vi, det = analysis["speech"], analysis["vision"], analysis["details"]
    voice, lang, body, conf = [], [], [], []

    if sp.get("fluency_score") is not None:
        voice.append(_metric("fluency", "Fluency", sp["fluency_score"], f"{sp['fluency_score']:.0f}/100",
                             sp["fluency_score"], "70+", "smooth speech, few long pauses"))
    if sp.get("speaking_rate"):
        voice.append(_metric("pace", "Speaking pace", sp["speaking_rate"], f"{sp['speaking_rate']:.0f} wpm",
                             pace_score(sp["speaking_rate"]), "120–160 wpm"))
    if sp.get("pronunciation_score") is not None:
        pr = det.get("pronunciation") or {}
        hint = ("clarity, Malaysian accent allowed" if pr.get("method") != "phone-gop" else
                f"{len(pr.get('intelligibility') or [])} unclear sound(s); "
                f"{len(pr.get('regional') or [])} Malaysian English feature(s) accepted")
        voice.append(_metric("pronunciation", "Pronunciation", sp["pronunciation_score"],
                             f"{sp['pronunciation_score']:.0f}/100", sp["pronunciation_score"], "70+", hint))
    if prosody:
        voice.append(_metric("vocal_variety", "Vocal variety", prosody.pitch_variation_st,
                             f"{prosody.pitch_variation_st:.1f} semitones", pitch_score(prosody.pitch_variation_st),
                             "2–7 semitones", "pitch movement; under 2 sounds monotone"))
        voice.append(_metric("loudness", "Volume & steadiness", prosody.loudness_dbfs,
                             f"{prosody.loudness_dbfs:.0f} dBFS ±{prosody.loudness_variation_db:.0f}",
                             loudness_score(prosody.loudness_dbfs, prosody.loudness_variation_db),
                             "louder than −35 dBFS, ±7 dB", "how loud and how steady"))

    if sp.get("filler_per_minute") is not None:
        lang.append(_metric("fillers", "Filler words", sp["filler_per_minute"], f"{sp['filler_per_minute']:.1f}/min",
                            filler_score(sp["filler_per_minute"]), "under 2/min"))
    if lang_use and lang_use.vocabulary_richness is not None:
        lang.append(_metric("vocabulary", "Vocabulary richness", lang_use.vocabulary_richness,
                            f"{lang_use.vocabulary_richness * 100:.0f}% varied",
                            richness_score(lang_use.vocabulary_richness), "65%+", "different words per 50"))
    if lang_use:
        lang.append(_metric("hedging", "Hedging phrases", lang_use.hedges_per_100_words,
                            f"{lang_use.hedge_count} ({lang_use.hedges_per_100_words:.1f} per 100 words)",
                            hedge_score(lang_use.hedges_per_100_words), "under 1 per 100 words",
                            "\"I think\", \"maybe\", \"kind of\""))
    stut = det.get("stuttering") or {}
    if stut.get("stuttering_score") is not None and sp.get("speaking_rate"):
        lang.append(_metric("disfluency", "Repetitions & blocks", stut["stuttering_score"],
                            f"{len(stut.get('detected_events') or [])} events", _clamp(100 - stut["stuttering_score"]), "0–2 events"))

    if vi.get("eye_contact_score") is not None:
        body.append(_metric("eye_contact", "Eye contact", vi["eye_contact_score"], f"{vi['eye_contact_score']:.0f}%",
                            vi["eye_contact_score"], "70%+", "looking at the lens"))
    if vi.get("posture_score") is not None:
        body.append(_metric("posture", "Posture", vi["posture_score"], f"{vi['posture_score']:.0f}/100",
                            vi["posture_score"], "75+", "upright, level, still"))
    if gestures:
        body.append(_metric("gestures", "Hand gestures", gestures.gesture_ratio,
                            f"{gestures.gesture_ratio * 100:.0f}% of the time", gesture_score(gestures),
                            "20–60% of the time", "hands visible and moving"))
        body.append(_metric("head_stability", "Head steadiness", gestures.head_stability,
                            f"{gestures.head_stability:.0f}/100", gestures.head_stability, "70+"))

    if vi.get("confidence_score") is not None:
        conf.append(_metric("confidence", "Confidence", vi["confidence_score"], f"{vi['confidence_score']:.0f}/100",
                            vi["confidence_score"], "70+", "11 cues: pace, pauses, repetitions, stutters, fillers, response time, face, posture, eye contact"))
    emo = det.get("emotion") or {}
    if emo.get("facial_tension") is not None:
        conf.append(_metric("expression", "Relaxed expression", emo["facial_tension"],
                            f"mostly {emo.get('dominant_emotion', 'neutral')}", _clamp(100 - emo["facial_tension"]),
                            "tension under 30"))
    lat = median_latency(client_metrics)
    if lat is not None:
        conf.append(_metric("response_time", "Response time", lat, f"{lat:.1f} s", latency_score(lat), "under 2 s",
                            "from the end of a question to your first word"))
    if tunneling:
        # Only a link that beats chance (p < 0.05) costs points; a chance-level r is no evidence
        r = tunneling["r"]
        score = _clamp(100 - max(0.0, r) * 100) if tunneling["p"] < 0.05 else 100.0
        conf.append(_metric("gaze_tunneling", "Gaze Tunneling", r, f"r = {r:.2f} · {tunneling['label'].lower()}", score,
                            "no significant link", "looking away when you stumble"))

    def pillar(key, label, items, blurb):
        scores = [m["score"] for m in items if m["score"] is not None]
        score = round(statistics.mean(scores), 1) if scores else None
        return {"key": key, "label": label, "score": score, "status": _status(score), "about": blurb, "metrics": items}

    return {
        "voice": pillar("voice", "Voice & delivery", voice, "How you sound: pace, fluency, clarity, variety, volume."),
        "language": pillar("language", "Language & clarity", lang, "The words you choose: fillers, vocabulary, hedging."),
        "body": pillar("body", "Body language", body, "How you look: eye contact, posture, gestures."),
        "confidence": pillar("confidence", "Confidence & presence", conf, "How sure you come across, and how quickly you respond."),
    }


def as_dict(result) -> dict | None:
    return asdict(result) if result is not None else None
