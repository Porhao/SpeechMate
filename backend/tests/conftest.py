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
os.environ["LLM_BASE_URL"] = ""
os.environ["TTS_BASE_URL"] = ""
# Deterministic and offline even where requirements-ml.txt is installed
os.environ["USE_LOCAL_ML"] = "false"
os.environ["MAX_CONCURRENT_JOBS"] = "2"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes"
# Tests create sessions freely; test_privacy.py switches the consent gate back on
os.environ["REQUIRE_CLOUD_CONSENT"] = "false"

# Use a system ffmpeg if present, otherwise the pip-installed static build
if not shutil.which(os.environ.get("FFMPEG_BIN", "ffmpeg")):
    try:
        import imageio_ffmpeg

        os.environ["FFMPEG_BIN"] = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


import pytest  # noqa: E402


async def sign_in(client, email: str = "aisyah@example.com") -> dict:
    """Register + sign in; returns the Authorization header (every deck and live route needs one)."""
    r = await client.post("/api/auth/register", json={
        "full_name": "Aisyah", "email": email, "password": "correct-horse", "communication_goal": "Improve Presentations",
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/auth/login", json={"email": email.upper(), "password": "correct-horse"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Rate-limit windows are process-wide; every test starts with none used."""
    from app.limits import limiter

    limiter.reset()
    yield
