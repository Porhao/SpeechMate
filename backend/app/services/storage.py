"""Local file storage: one folder per deck (its upload and slide images) and per live session
(its recording and analysis work files), under STORAGE_BASE_PATH. Rows store paths relative to it."""

import shutil
import uuid
from pathlib import Path

from app.config import settings


def deck_folder(deck_id: uuid.UUID | str) -> str:
    return str(deck_id)


def live_folder(live_id: uuid.UUID | str) -> str:
    return f"live/{live_id}"


class StorageService:
    def __init__(self):
        self.base_path = Path(settings.storage_base_path).resolve()

    def path(self, folder: str, filename: str = "") -> Path:
        """Absolute path of a file (or, without `filename`, the folder) in `folder`."""
        return self.base_path / folder / filename if filename else self.base_path / folder

    def ensure_session_dirs(self, folder: str) -> dict[str, Path]:
        """Create a deck folder and its slides/ subfolder."""
        dirs = {"root": self.path(folder), "slides": self.path(folder, "slides")}
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)
        return dirs

    def relative(self, path: Path) -> str:
        return path.relative_to(self.base_path).as_posix()

    def get_absolute_path(self, relative_path: str) -> Path:
        return self.base_path / relative_path

    def delete_folder(self, folder: str) -> None:
        if (d := self.path(folder)).exists():
            shutil.rmtree(d)


storage_service = StorageService()
