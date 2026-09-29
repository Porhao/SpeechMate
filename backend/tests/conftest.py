"""Test configuration.

Tests run against SQLite + a temp storage dir, with all AI keys blanked so
every stage exercises its offline fallback. Environment variables must be
set before any `app.*` import, because settings/engine are module globals.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="speechmate-tests-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp / 'test.db'}"
os.environ["STORAGE_BASE_PATH"] = str(_tmp / "storage")
os.environ["OPENAI_API_KEY"] = ""
os.environ["ELEVENLABS_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = ""
# Deterministic and offline even where requirements-ml.txt is installed
os.environ["USE_LOCAL_ML"] = "false"
os.environ["MAX_CONCURRENT_JOBS"] = "2"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes"

# Use a system ffmpeg if present, otherwise the pip-installed static build
if not shutil.which(os.environ.get("FFMPEG_BIN", "ffmpeg")):
    try:
        import imageio_ffmpeg

        os.environ["FFMPEG_BIN"] = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
