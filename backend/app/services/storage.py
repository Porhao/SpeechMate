"""
Local Disk Storage — session media
Saves the browser-recorded webm (audio+video together) per session and
resolves it back for analysis. Swap for a MinIO/S3-backed implementation
in production; the interface (save_upload / get_media_path) stays the same.
"""
from pathlib import Path
from fastapi import UploadFile

STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage"
RECORDINGS_DIR = STORAGE_ROOT / "recordings"


def _ensure_dir() -> None:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def _extension_for(filename: str | None) -> str:
    if filename and "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return "webm"


async def save_upload(session_id: str, file: UploadFile) -> Path:
    """
    Save an uploaded recording for a session, overwriting any previous
    upload for the same session_id (audio and video uploads both land on
    the same file — a session's recording is a single webm blob containing
    both tracks).
    """
    _ensure_dir()
    ext = _extension_for(file.filename)
    dest = RECORDINGS_DIR / f"{session_id}.{ext}"

    # Clear any prior recording under a different extension for this session
    for existing in RECORDINGS_DIR.glob(f"{session_id}.*"):
        if existing != dest:
            existing.unlink(missing_ok=True)

    contents = await file.read()
    dest.write_bytes(contents)
    return dest


def get_media_path(session_id: str) -> Path | None:
    """Resolve the saved recording for a session, if any."""
    if not RECORDINGS_DIR.exists():
        return None
    matches = list(RECORDINGS_DIR.glob(f"{session_id}.*"))
    return matches[0] if matches else None
