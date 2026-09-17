"""
Shared video frame sampling for the vision analyzers.
Uses OpenCV's VideoCapture (the opencv-python wheel ships its own bundled
FFmpeg support, so no system ffmpeg binary is required to decode webm).
"""
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

logger = logging.getLogger(__name__)

# Some inputs (e.g. an audio-only container someone fed in as "video") can
# make cv2.VideoCapture.read() block indefinitely on this backend instead of
# cleanly reporting EOF/failure. That's a native (C++) call Python can't
# interrupt from within the loop, so we run it in a worker thread and give
# up after a timeout rather than hang the request forever.
OPEN_TIMEOUT_SECONDS = 15


def sample_frames(video_path: str, max_frames: int = 60):
    """
    Evenly sample up to `max_frames` RGB frames across the video's duration.
    Returns a list of numpy arrays (H, W, 3) in RGB order. Returns an empty
    list if the video can't be opened, has no readable frames, or decoding
    doesn't finish within a timeout — callers should treat that as "fall
    back to stub".
    """
    # Not using a `with` block deliberately: ThreadPoolExecutor.__exit__ calls
    # shutdown(wait=True), which would block on the abandoned worker below if
    # the native cv2 call never returns. shutdown(wait=False) lets us give up
    # on time without waiting for a thread that may never finish.
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_sample_frames_blocking, video_path, max_frames)
    try:
        return future.result(timeout=OPEN_TIMEOUT_SECONDS)
    except FutureTimeoutError:
        logger.warning(
            "Timed out sampling frames from %s after %ss — treating as unreadable",
            video_path, OPEN_TIMEOUT_SECONDS,
        )
        return []
    finally:
        pool.shutdown(wait=False)


def _sample_frames_blocking(video_path: str, max_frames: int):
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("Could not open video for frame sampling: %s", video_path)
        return []

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []

    if total <= 0:
        # Some containers don't report frame count reliably — read
        # sequentially, but cap total attempts so a stream that never
        # signals EOF can't spin forever.
        max_attempts = max_frames * 20
        attempts = 0
        while attempts < max_attempts and len(frames) < max_frames:
            ok, frame = cap.read()
            attempts += 1
            if not ok:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        cap.release()
        return frames

    step = max(total // max_frames, 1)
    idx = 0
    while idx < total and len(frames) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if ok:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        idx += step

    cap.release()
    return frames
