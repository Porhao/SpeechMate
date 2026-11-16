"""Vision analysis of a live-session recording: gaze (eye contact + its timeline), body (posture,
gestures, head steadiness) and facial emotion.

- Gaze: MediaPipe Face Mesh with refined iris landmarks, ~2 samples a second over the whole
  video; the iris position within each eye classifies gaze as camera / left / right / down.
- Body: one MediaPipe Pose pass over sampled frames — head tilt, shoulder level, torso
  movement, seated-posture problems, hand movement and head steadiness.
- Emotion: MediaPipe face detection crop + a pretrained ViT facial-expression
  classifier (trpakov/vit-face-expression, FER2013 7-class) on CPU.

All blocking — the pipeline runs them via asyncio.to_thread. The models are shared, process-wide
singletons and not thread-safe: the pipeline lets one analysis at a time use them.
"""

import logging
import math
import statistics
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import asdict, dataclass

from app.services.live import rules
from app.services.live._ml import load_once

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
NOSE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_WRIST, RIGHT_WRIST = 0, 7, 8, 11, 12, 15, 16
# Seated-posture checks (calibration knobs: ratios, so the distance to the camera doesn't matter)
VISIBLE = 0.5            # pose landmark visibility needed to count a shoulder as in view
MIN_NECK_RATIO = 0.3     # (shoulder line y − ear line y) ÷ shoulder width: ~0.45–0.6 sitting upright; slumped or lying back sinks the head into the shoulders
MIN_NOSE_DROP = -0.1     # (nose y − ear line y) ÷ ear-to-ear distance: ~0.1–0.25 with the camera at eye level; below that the camera looks up from below (laptop on the lap, in bed)

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
    head_alignment: float | None       # None when you were never in view
    shoulder_alignment: float | None
    body_stability: float | None
    excessive_movement: bool
    tilt_angle: float
    in_frame_pct: float = 100.0          # % of frames with both shoulders in view
    upright_pct: float | None = None     # % of in-view frames sitting upright with the camera at eye level
    slouched_pct: float = 0.0            # % of in-view frames slumped / lying back
    camera_low_pct: float = 0.0          # % of in-view frames filmed from below (laptop on lap, in bed)


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

def _with_timeout(fn, *args, timeout: float, label: str) -> list:
    """`fn(*args)` (a video read), or [] if it takes longer than `timeout`."""
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(fn, *args)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        logger.warning("Timed out %s", label)
        return []
    finally:
        pool.shutdown(wait=False)  # don't wait on a native call that may never return


def sample_frames(video_path: str, max_frames: int = 60) -> list:
    """Evenly sample up to `max_frames` RGB frames. Empty list if unreadable (e.g. audio-only)."""
    return _with_timeout(_sample_frames_blocking, video_path, max_frames, timeout=FRAME_READ_TIMEOUT_SEC,
                         label=f"sampling frames from {video_path}")


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


# ── Gaze ────────────────────────────────────────────────────────────────────

@load_once
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


@dataclass
class GazeSample:
    t_sec: float   # on the audio's timeline
    gaze: str      # camera | left | right | down
    h: float       # horizontal iris position, 0-1


GAZE_FPS = 2.0                 # samples per second: fine enough for 5 s Gaze Tunneling windows
GAZE_TIMEOUT_SEC = 180


def gaze_samples(video_path: str, duration_sec: float) -> list[GazeSample]:
    """A gaze sample at ~GAZE_FPS for every sampled frame with a face, on the same timeline as the
    audio (the recorder pauses video and audio together). Streams the file: one frame in memory at
    a time. Empty if unreadable or timed out."""
    return _with_timeout(_gaze_samples_blocking, video_path, duration_sec, timeout=GAZE_TIMEOUT_SEC,
                         label=f"reading the gaze from {video_path}")


def _gaze_samples_blocking(video_path: str, duration_sec: float) -> list[GazeSample]:
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if 5 <= fps <= 120 else 30.0   # browser webm often reports 1000 or 0
    step = max(int(round(fps / GAZE_FPS)), 1)
    samples, idx = [], 0                      # (frame index, gaze, h)
    while idx < int(duration_sec * 120) + 1000:  # cap for a stream that never signals EOF
        if idx % step:
            if not cap.grab():
                break
        else:
            ok, frame = cap.read()
            if not ok:
                break
            result = _face_mesh().process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if result.multi_face_landmarks:
                samples.append((idx, *_gaze(result.multi_face_landmarks[0].landmark)))
        idx += 1
    cap.release()
    if not samples or idx == 0:
        return []
    # Frame position → seconds, scaled to the audio's length (robust to a wrong reported fps)
    return [GazeSample(i / idx * duration_sec, g, h) for i, g, h in samples]


def eye_contact(samples: list[GazeSample]) -> EyeContactResult | None:
    if not samples:
        return None
    gazes = [s.gaze for s in samples]
    look_away = sum(1 for g in gazes if g != "camera")
    pct = round(look_away / len(gazes) * 100, 1)
    return EyeContactResult(
        eye_contact_score=round(100 - pct, 1),
        gaze_consistency=round(max(0.0, 100 - statistics.pstdev(s.h for s in samples) * 200), 1) if len(samples) > 1 else 100.0,
        look_away_count=look_away,
        look_away_percentage=pct,
        dominant_gaze=max(set(gazes), key=gazes.count),
        frame_count=len(gazes),
    )


# ── Posture ─────────────────────────────────────────────────────────────────

@load_once
def _pose():
    import mediapipe as mp

    return mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1, min_detection_confidence=0.5)


def posture_issue(lm, aspect: float = 16 / 9) -> str | None:
    """One frame's seated-posture problem, or None when upright and in view:
    "out_of_frame" (shoulders not in view: too close, or lying down), "slouched", "camera_low".
    `lm`: pose landmarks (x, y in 0-1 of the frame, visibility); `aspect`: frame width ÷ height."""
    shoulders = (lm[LEFT_SHOULDER], lm[RIGHT_SHOULDER])
    if any(getattr(p, "visibility", 1.0) < VISIBLE or not 0 <= p.y <= 1 for p in shoulders):
        return "out_of_frame"
    ear_y = (lm[LEFT_EAR].y + lm[RIGHT_EAR].y) / 2
    shoulder_w = abs(shoulders[0].x - shoulders[1].x) * aspect
    if shoulder_w > 0 and ((shoulders[0].y + shoulders[1].y) / 2 - ear_y) / shoulder_w < MIN_NECK_RATIO:
        return "slouched"
    ear_w = math.hypot((lm[LEFT_EAR].x - lm[RIGHT_EAR].x) * aspect, lm[LEFT_EAR].y - lm[RIGHT_EAR].y)
    if ear_w > 0 and (lm[NOSE].y - ear_y) / ear_w < MIN_NOSE_DROP:
        return "camera_low"
    return None


@dataclass
class GestureResult:
    hands_visible_ratio: float     # share of frames with at least one hand in view
    gesture_ratio: float           # share of frames where a visible hand moved noticeably
    head_stability: float          # 0–100 (nose movement relative to the shoulders)
    frame_count: int


def analyze_body(frames: list) -> tuple[PostureResult | None, GestureResult | None]:
    """One Pose pass. Posture: alignment (head, shoulders, steadiness) on the frames where you're in
    view, scaled by the share of the session you sat upright, in view, with the camera at eye level —
    lying in bed, slumping, or sitting so close your shoulders are cut off can't score well.
    Gestures: hands visible and moving, and how still the head is relative to the shoulders."""
    tilts, shoulder_diffs, torso_x, torso_y, issues = [], [], [], [], []
    visible, moving, heads, prev_wrists = 0, 0, [], None
    for frame in frames:
        result = _pose().process(frame)
        if not result.pose_landmarks:
            prev_wrists = None
            continue
        lm = result.pose_landmarks.landmark
        width = abs(lm[LEFT_SHOULDER].x - lm[RIGHT_SHOULDER].x) or 0.2
        mid_x = (lm[LEFT_SHOULDER].x + lm[RIGHT_SHOULDER].x) / 2
        mid_y = (lm[LEFT_SHOULDER].y + lm[RIGHT_SHOULDER].y) / 2
        heads.append(((lm[NOSE].x - mid_x) / width, (lm[NOSE].y - mid_y) / width))
        wrists = [(lm[i].x, lm[i].y) for i in (LEFT_WRIST, RIGHT_WRIST) if lm[i].visibility > VISIBLE and lm[i].y < 1.0]
        if wrists:
            visible += 1
            if prev_wrists and max(math.dist(a, b) for a in wrists for b in prev_wrists) / width > 0.15:
                moving += 1
        prev_wrists = wrists or None

        issue = posture_issue(lm, frame.shape[1] / frame.shape[0])
        issues.append(issue)
        if issue == "out_of_frame":
            continue
        tilts.append(math.degrees(math.atan2(lm[RIGHT_EAR].y - lm[LEFT_EAR].y, lm[RIGHT_EAR].x - lm[LEFT_EAR].x)))
        shoulder_diffs.append(abs(lm[LEFT_SHOULDER].y - lm[RIGHT_SHOULDER].y))
        torso_x.append(mid_x)
        torso_y.append(mid_y)
    gestures = None
    if len(heads) >= 3:
        hx, hy = statistics.pstdev(h[0] for h in heads), statistics.pstdev(h[1] for h in heads)
        gestures = GestureResult(hands_visible_ratio=round(visible / len(heads), 2), gesture_ratio=round(moving / len(heads), 2),
                                 head_stability=rules.clamp(100 - (hx + hy) * 250), frame_count=len(heads))
    return posture_from(issues, tilts, shoulder_diffs, torso_x, torso_y), gestures


def posture_from(issues: list[str | None], tilts: list[float], shoulder_diffs: list[float],
                 torso_x: list[float], torso_y: list[float]) -> PostureResult | None:
    """The score from per-frame measurements (split out so it's testable without video)."""
    if not issues:
        return None
    pct = lambda n, of: round(n / of * 100, 1) if of else 0.0  # noqa: E731
    in_view = [i for i in issues if i != "out_of_frame"]
    in_frame = pct(len(in_view), len(issues))
    good = pct(in_view.count(None), len(issues))       # upright, in view, camera level: share of ALL frames
    if not tilts:  # never in view: alignment can't be judged, and the score reflects that
        return PostureResult(posture_score=0.0, head_alignment=None, shoulder_alignment=None, body_stability=None,
                             excessive_movement=False, tilt_angle=0.0,
                             in_frame_pct=in_frame, upright_pct=None)
    avg_tilt = statistics.mean(tilts)
    head = round(max(0.0, 100 - abs(avg_tilt) * 4), 1)
    shoulders = round(max(0.0, 100 - statistics.mean(shoulder_diffs) * 500), 1)
    movement = statistics.pstdev(torso_x) + statistics.pstdev(torso_y) if len(torso_x) > 1 else 0.0
    stability = round(max(0.0, 100 - movement * 800), 1)
    slouched, camera_low = pct(in_view.count("slouched"), len(in_view)), pct(in_view.count("camera_low"), len(in_view))

    return PostureResult(
        posture_score=round((head + shoulders + stability) / 3 * good / 100, 1),
        head_alignment=head,
        shoulder_alignment=shoulders,
        body_stability=stability,
        excessive_movement=stability < 50,
        tilt_angle=round(avg_tilt, 1),
        in_frame_pct=in_frame,
        upright_pct=pct(in_view.count(None), len(in_view)),
        slouched_pct=slouched,
        camera_low_pct=camera_low,
    )


# ── Facial emotion ──────────────────────────────────────────────────────────

@load_once
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
    step = max(len(frames) // 12, 1)  # ~1 s per frame on CPU: 12 frames are plenty for a mood read
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
