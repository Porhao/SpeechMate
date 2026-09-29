"""Vision analysis of a live-session recording: eye contact, posture, facial emotion.

- Eye contact: MediaPipe Face Mesh with refined iris landmarks — the iris
  position within each eye classifies gaze as camera / left / right / down.
- Posture: MediaPipe Pose — head tilt from the ear line, shoulder level, and
  torso-midpoint movement across frames for stability.
- Emotion: MediaPipe face detection crop + a pretrained ViT facial-expression
  classifier (trpakov/vit-face-expression, FER2013 7-class) on CPU.

All blocking — the pipeline runs them via asyncio.to_thread.
"""

import logging
import math
import statistics
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import asdict, dataclass, field
from functools import lru_cache

logger = logging.getLogger(__name__)

# Some inputs make cv2.VideoCapture.read() block forever instead of reporting
# EOF; that's a native call Python can't interrupt, so give up after a timeout.
FRAME_READ_TIMEOUT_SEC = 15

# Face Mesh landmark indices (refine_landmarks=True adds iris points 468–477)
LEFT_IRIS, RIGHT_IRIS = 468, 473
LEFT_EYE_OUTER, LEFT_EYE_INNER, LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 33, 133, 159, 145
RIGHT_EYE_INNER, RIGHT_EYE_OUTER, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 362, 263, 386, 374
H_CENTER_LO, H_CENTER_HI = 0.35, 0.65
V_DOWN_THRESHOLD = 0.62

# Pose landmark indices
LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER = 7, 8, 11, 12

EMOTION_MODEL = "trpakov/vit-face-expression"
# How much each expression contributes to perceived speaking confidence
EMOTION_CONFIDENCE_WEIGHT = {
    "happy": 0.90, "neutral": 0.75, "surprised": 0.60, "sad": 0.45,
    "fearful": 0.30, "nervous": 0.25, "angry": 0.35,
}
# The model's labels onto ours; "disgust" folds into the nearest negative bucket
HF_LABEL_MAP = {
    "happy": "happy", "neutral": "neutral", "surprise": "surprised", "fear": "fearful",
    "sad": "sad", "angry": "angry", "disgust": "angry",
}


@dataclass
class EyeContactResult:
    eye_contact_score: float     # 0–100
    gaze_consistency: float      # 0–100
    look_away_count: int
    look_away_percentage: float
    dominant_gaze: str           # camera | left | right | down
    frame_count: int


@dataclass
class PostureResult:
    posture_score: float
    head_alignment: float
    shoulder_alignment: float
    body_stability: float
    excessive_movement: bool
    tilt_angle: float
    recommendations: list[str] = field(default_factory=list)


@dataclass
class EmotionResult:
    dominant_emotion: str
    confidence_level: float                  # 0–100 speaking confidence from expression
    emotion_distribution: dict[str, float]
    facial_tension: float                    # 0–100, lower = more relaxed
    expression_stability: float              # 0–100
    frame_count: int


def as_dict(result) -> dict | None:
    return asdict(result) if result is not None else None


# ── Frame sampling ──────────────────────────────────────────────────────────

def sample_frames(video_path: str, max_frames: int = 60) -> list:
    """Evenly sample up to `max_frames` RGB frames. Empty list if unreadable (e.g. audio-only)."""
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_sample_frames_blocking, video_path, max_frames)
    try:
        return future.result(timeout=FRAME_READ_TIMEOUT_SEC)
    except FutureTimeoutError:
        logger.warning("Timed out sampling frames from %s", video_path)
        return []
    finally:
        pool.shutdown(wait=False)  # don't wait on a native call that may never return


def _sample_frames_blocking(video_path: str, max_frames: int) -> list:
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    frames = []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        # Browser webm often has no frame count: read sequentially, keep every Nth,
        # with a cap so a stream that never signals EOF can't spin forever.
        all_frames, attempts = [], 0
        while attempts < max_frames * 60:
            ok, frame = cap.read()
            attempts += 1
            if not ok:
                break
            all_frames.append(frame)
        step = max(len(all_frames) // max_frames, 1)
        frames = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in all_frames[::step][:max_frames]]
    else:
        step = max(total // max_frames, 1)
        for idx in range(0, total, step):
            if len(frames) >= max_frames:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok:
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames


# ── Eye contact ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _face_mesh():
    import mediapipe as mp

    return mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5
    )


def _gaze(lm) -> tuple[str, float]:
    def ratio(point, a, b, axis):
        lo, hi = sorted([getattr(lm[a], axis), getattr(lm[b], axis)])
        return (getattr(lm[point], axis) - lo) / max(hi - lo, 1e-6)

    h = (ratio(LEFT_IRIS, LEFT_EYE_OUTER, LEFT_EYE_INNER, "x")
         + ratio(RIGHT_IRIS, RIGHT_EYE_OUTER, RIGHT_EYE_INNER, "x")) / 2
    v = (ratio(LEFT_IRIS, LEFT_EYE_TOP, LEFT_EYE_BOTTOM, "y")
         + ratio(RIGHT_IRIS, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM, "y")) / 2
    if v > V_DOWN_THRESHOLD:
        return "down", h
    if h < H_CENTER_LO:
        return "left", h
    if h > H_CENTER_HI:
        return "right", h
    return "camera", h


def analyze_eye_contact(frames: list) -> EyeContactResult | None:
    gazes, h_ratios = [], []
    for frame in frames:
        result = _face_mesh().process(frame)
        if result.multi_face_landmarks:
            g, h = _gaze(result.multi_face_landmarks[0].landmark)
            gazes.append(g)
            h_ratios.append(h)
    if not gazes:
        return None

    look_away = sum(1 for g in gazes if g != "camera")
    pct = round(look_away / len(gazes) * 100, 1)
    return EyeContactResult(
        eye_contact_score=round(100 - pct, 1),
        gaze_consistency=round(max(0.0, 100 - statistics.pstdev(h_ratios) * 200), 1) if len(h_ratios) > 1 else 100.0,
        look_away_count=look_away,
        look_away_percentage=pct,
        dominant_gaze=max(set(gazes), key=gazes.count),
        frame_count=len(gazes),
    )


# ── Posture ─────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _pose():
    import mediapipe as mp

    return mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1, min_detection_confidence=0.5)


def analyze_posture(frames: list) -> PostureResult | None:
    tilts, shoulder_diffs, torso_x, torso_y = [], [], [], []
    for frame in frames:
        result = _pose().process(frame)
        if not result.pose_landmarks:
            continue
        lm = result.pose_landmarks.landmark
        tilts.append(math.degrees(math.atan2(lm[RIGHT_EAR].y - lm[LEFT_EAR].y, lm[RIGHT_EAR].x - lm[LEFT_EAR].x)))
        shoulder_diffs.append(abs(lm[LEFT_SHOULDER].y - lm[RIGHT_SHOULDER].y))
        torso_x.append((lm[LEFT_SHOULDER].x + lm[RIGHT_SHOULDER].x) / 2)
        torso_y.append((lm[LEFT_SHOULDER].y + lm[RIGHT_SHOULDER].y) / 2)
    if not tilts:
        return None

    avg_tilt = statistics.mean(tilts)
    head = round(max(0.0, 100 - abs(avg_tilt) * 4), 1)
    shoulders = round(max(0.0, 100 - statistics.mean(shoulder_diffs) * 500), 1)
    movement = statistics.pstdev(torso_x) + statistics.pstdev(torso_y) if len(torso_x) > 1 else 0.0
    stability = round(max(0.0, 100 - movement * 800), 1)

    recs = []
    if head < 70:
        recs.append("Keep your head upright and avoid excessive nodding.")
    if shoulders < 70:
        recs.append("Level your shoulders to project confidence.")
    if stability < 60:
        recs.append("Reduce body swaying to appear more composed.")

    return PostureResult(
        posture_score=round((head + shoulders + stability) / 3, 1),
        head_alignment=head,
        shoulder_alignment=shoulders,
        body_stability=stability,
        excessive_movement=stability < 50,
        tilt_angle=round(avg_tilt, 1),
        recommendations=recs,
    )


# ── Facial emotion ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _emotion_models():
    import mediapipe as mp
    from transformers import pipeline

    logger.info("Loading facial expression model '%s' (CPU)…", EMOTION_MODEL)
    return (
        pipeline("image-classification", model=EMOTION_MODEL, device=-1),
        mp.solutions.face_detection.FaceDetection(min_detection_confidence=0.5),
    )


def _classify(frame, classifier, detector) -> dict[str, float] | None:
    from PIL import Image

    h, w, _ = frame.shape
    det = detector.process(frame)
    if not det.detections:
        return None
    box = det.detections[0].location_data.relative_bounding_box
    x1, y1 = max(int(box.xmin * w), 0), max(int(box.ymin * h), 0)
    x2, y2 = min(int((box.xmin + box.width) * w), w), min(int((box.ymin + box.height) * h), h)
    if x2 <= x1 or y2 <= y1:
        return None

    dist: dict[str, float] = {}
    for pred in classifier(Image.fromarray(frame[y1:y2, x1:x2])):
        label = HF_LABEL_MAP.get(pred["label"].lower())
        if label:
            dist[label] = dist.get(label, 0.0) + pred["score"]
    total = sum(dist.values())
    return {k: v / total for k, v in dist.items()} if total > 0 else None


def analyze_emotion(frames: list) -> EmotionResult | None:
    classifier, detector = _emotion_models()
    # The most expensive per-frame op: use fewer frames than eye contact/posture
    step = max(len(frames) // 24, 1)
    dists = [d for f in frames[::step] if (d := _classify(f, classifier, detector))]
    if not dists:
        return None

    confidences = [sum(EMOTION_CONFIDENCE_WEIGHT.get(e, 0.5) * p for e, p in d.items()) * 100 for d in dists]
    avg = {e: round(sum(d.get(e, 0.0) for d in dists) / len(dists), 3) for e in EMOTION_CONFIDENCE_WEIGHT}
    avg = {k: v for k, v in avg.items() if v > 0}
    return EmotionResult(
        dominant_emotion=max(avg, key=avg.get),
        confidence_level=round(sum(confidences) / len(confidences), 1),
        emotion_distribution=avg,
        facial_tension=round((avg.get("fearful", 0) + avg.get("angry", 0) + avg.get("sad", 0)) * 100, 1),
        expression_stability=round(max(0.0, 100 - statistics.pstdev(confidences) * 1.5), 1) if len(confidences) > 1 else 100.0,
        frame_count=len(dists),
    )
