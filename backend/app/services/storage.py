"""Local file storage service.

Abstracts file I/O so we can swap to S3/Supabase Storage later
without changing callers.
"""

import shutil
from pathlib import Path

from app.config import settings


class StorageService:
    """Manages file storage for decks (upload, slide PNGs) and live-session recordings."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.storage_base_path).resolve()

    def _session_dir(self, session_id: str) -> Path:
        return self.base_path / session_id

    def ensure_session_dirs(self, session_id: str) -> dict[str, Path]:
        """Create the per-session directory structure and return paths."""
        session_dir = self._session_dir(session_id)
        dirs = {
            "root": session_dir,
            "slides": session_dir / "slides",
        }
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        return dirs

    async def save_upload_limited(self, session_id: str, filename: str, file, max_bytes: int, what: str) -> str:
        """Stream an UploadFile to storage with a size cap (413 above it); returns the relative path."""
        from app.limits import save_limited

        file_path = self._session_dir(session_id) / filename
        await save_limited(file, file_path, max_bytes, what)
        return self.relative(file_path)

    def relative(self, path: Path) -> str:
        """Convert an absolute path under the storage root to a storage-relative path."""
        return path.relative_to(self.base_path).as_posix()

    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert a storage-relative path to an absolute path."""
        return self.base_path / relative_path

    def delete_session(self, session_id: str) -> None:
        """Remove all stored files for a session."""
        session_dir = self._session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)


# Module-level singleton
storage_service = StorageService()
