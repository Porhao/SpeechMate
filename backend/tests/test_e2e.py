"""End-to-end API test: upload → ideal video → practice → OIS feedback → chat.

Runs fully offline (no AI keys). Needs ffmpeg. If LibreOffice isn't
installed, slide rendering is replaced by a Pillow renderer so every other
stage still runs for real.
"""

import io
import math
import shutil
import struct
import wave
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageDraw

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.services import pipeline, tasks
from app.services.slide_processor import slide_processor
from app.services.storage import storage_service
from make_sample_deck import build as build_sample_deck

pytestmark = pytest.mark.skipif(
    shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required for the end-to-end test"
)


async def _pillow_render(session_id: str, pptx_relative_path: str) -> list[Path]:
    slides_dir = storage_service.ensure_session_dirs(session_id)["slides"]
    paths = []
    for i, text in enumerate(slide_processor.extract_slide_texts(pptx_relative_path), start=1):
        img = Image.new("RGB", (1920, 1080), "white")
        ImageDraw.Draw(img).multiline_text((100, 100), text, fill="black")
        path = slides_dir / f"slide_{i}.png"
        img.save(path)
        paths.append(path)
    return paths


def _tone_wav(pattern: list[tuple[float, bool]]) -> bytes:
    """WAV of tone bursts (stand-in for speech) and silences, e.g. [(5, True), (3, False)]."""
    rate, frames = 16000, bytearray()
    for seconds, loud in pattern:
        for n in range(int(seconds * rate)):
            value = int(12000 * math.sin(2 * math.pi * 220 * n / rate)) if loud else 0
            frames += struct.pack("<h", value)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


@pytest.fixture
async def client(monkeypatch):
    if not (shutil.which(settings.libreoffice_bin) and shutil.which("pdftoppm")):
        monkeypatch.setattr(pipeline.slide_processor, "convert_pptx_to_pngs", _pillow_render)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_full_dual_agent_loop(client: httpx.AsyncClient, tmp_path: Path):
    deck = build_sample_deck(tmp_path / "deck.pptx")

    # Validation
    r = await client.post("/api/sessions", files={"pptx": ("deck.txt", b"x")})
    assert r.status_code == 400

    # ── Ideal Presentation Agent ─────────────────────────────────────────
    r = await client.post(
        "/api/sessions",
        files={"pptx": ("deck.pptx", deck.read_bytes())},
        data={"requirement_prompt": "first-year students"},
    )
    assert r.status_code == 201, r.text
    sid = r.json()["session_id"]

    # Practice before the ideal video exists must be rejected
    r = await client.post(f"/api/sessions/{sid}/practice", files={"audio": ("a.wav", b"x")})
    assert r.status_code == 409

    await tasks.wait_for_all(timeout=300)

    session = (await client.get(f"/api/sessions/{sid}")).json()
    assert session["status"] == "complete", session
    assert session["video_ready"] is True
    assert session["slide_count"] == 3
    assert session["slides_progress"] == {"rendered": 3, "scripted": 3, "synthesized": 3, "total": 3}
    assert session["voice_cloning_used"] is False
    assert any("slide text" in w for w in session["warnings"])  # offline script fallback noted

    scripts = (await client.get(f"/api/sessions/{sid}/scripts")).json()["slides"]
    assert [s["slide_index"] for s in scripts] == [1, 2, 3]
    assert all(s["script_text"] and s["script_source"] == "fallback" for s in scripts)
    assert scripts[1]["script_text"].count("Plan and Prioritize") == 1
    assert scripts[0]["start_sec"] == 0
    assert scripts[1]["start_sec"] == pytest.approx(scripts[0]["duration_sec"], abs=0.01)

    video = await client.get(f"/api/sessions/{sid}/video")
    assert video.status_code == 200
    assert video.headers["content-type"] == "video/mp4"
    assert video.content[4:8] == b"ftyp"

    assert (await client.get(f"/api/sessions/{sid}/slides/2/image")).status_code == 200
    slide_audio = await client.get(f"/api/sessions/{sid}/slides/1/audio")
    assert slide_audio.status_code == 200

    # ── Coach Agent ──────────────────────────────────────────────────────
    r = await client.post(
        f"/api/sessions/{sid}/practice",
        files={"audio": ("slide1.wav", slide_audio.content)},
        data={"recording_granularity": "per_slide", "slide_index": "9"},
    )
    assert r.status_code == 400

    # A silent recording is rejected with a helpful message
    r = await client.post(
        f"/api/sessions/{sid}/practice", files={"audio": ("silent.wav", _tone_wav([(4, False)]))}
    )
    silent_id = r.json()["practice_id"]
    await tasks.wait_for_all(timeout=120)
    silent = (await client.get(f"/api/sessions/{sid}/practice/{silent_id}")).json()
    assert silent["status"] == "failed" and "No speech" in silent["error_detail"]

    take = _tone_wav([(0.5, False), (6, True), (3, False), (6, True), (0.5, False)])
    r = await client.post(f"/api/sessions/{sid}/practice", files={"audio": ("take.wav", take)})
    assert r.status_code == 201, r.text
    pid = r.json()["practice_id"]
    await tasks.wait_for_all(timeout=120)

    practice = (await client.get(f"/api/sessions/{sid}/practice/{pid}")).json()
    assert practice["status"] == "complete", practice
    m = practice["metrics"]
    assert m["has_transcript"] is False
    assert m["duration_sec"] == pytest.approx(16.0, abs=0.2)
    assert m["pause_count"] == 1 and m["long_pauses"][0]["duration_sec"] == pytest.approx(3.0, abs=0.3)
    assert practice["feedback"]["encouragement"]
    assert 1 <= len(practice["feedback"]["observations"]) <= 3
    assert any("paused" in o["observation"] for o in practice["feedback"]["observations"])
    assert practice["audience_feedback"]["clarity_score"] >= 1
    assert any("OPENAI_API_KEY" in w for w in practice["warnings"])

    # Per-slide practice compares against that slide only
    r = await client.post(
        f"/api/sessions/{sid}/practice",
        files={"audio": ("slide1.wav", _tone_wav([(8, True)]))},
        data={"recording_granularity": "per_slide", "slide_index": "1"},
    )
    pid2 = r.json()["practice_id"]
    await tasks.wait_for_all(timeout=120)
    p2 = (await client.get(f"/api/sessions/{sid}/practice/{pid2}")).json()
    assert p2["status"] == "complete"
    assert p2["metrics"]["ideal_duration_sec"] < m["ideal_duration_sec"]

    listing = (await client.get(f"/api/sessions/{sid}/practice")).json()
    assert [p["practice_id"] for p in listing] == [silent_id, pid, pid2]

    # ── Chat ─────────────────────────────────────────────────────────────
    r = await client.post(f"/api/sessions/{sid}/practice/{pid}/chat", json={"message": "How do I improve?"})
    assert r.status_code == 200
    assert r.json()["role"] == "assistant" and r.json()["content"]
    history = (await client.get(f"/api/sessions/{sid}/practice/{pid}/chat")).json()["messages"]
    assert [msg["role"] for msg in history] == ["user", "assistant"]

    # ── Retry + delete ───────────────────────────────────────────────────
    r = await client.post(f"/api/sessions/{sid}/retry")
    assert r.status_code == 202
    await tasks.wait_for_all(timeout=300)
    assert (await client.get(f"/api/sessions/{sid}")).json()["status"] == "complete"

    assert (await client.delete(f"/api/sessions/{sid}")).status_code == 204
    assert (await client.get(f"/api/sessions/{sid}")).status_code == 404
    assert not (storage_service.base_path / sid).exists()
