"""End-to-end API test: upload a deck → it's prepared → present it in a live talk session.

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
from tests.conftest import sign_in

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


async def test_deck_then_presenting_it(client: httpx.AsyncClient, tmp_path: Path):
    """Upload → the deck is prepared (slides + insights + Q&A plan, no example video) → the user
    presents it in a live "talk" session → the analysis judges the talk slide by slide."""
    deck = build_sample_deck(tmp_path / "deck.pptx")
    headers = await sign_in(client, "a@example.com")

    r = await client.post("/api/sessions", headers=headers, files={"pptx": ("deck.txt", b"x")})
    assert r.status_code == 400

    r = await client.post("/api/sessions", headers=headers, files={"pptx": ("deck.pptx", deck.read_bytes())},
                          data={"requirement_prompt": "first-year students"})
    assert r.status_code == 201, r.text
    sid = r.json()["session_id"]
    await tasks.wait_for_all(timeout=300)

    session = (await client.get(f"/api/sessions/{sid}", headers=headers)).json()
    assert session["status"] == "complete", session
    assert session["slide_count"] == 3 and session["slides_rendered"] == 3
    assert session["insights"]["qa_plan"]["questions"]           # Q&A ready to start instantly
    assert (await client.get(f"/api/sessions/{sid}/slides/2/image", headers=headers)).status_code == 200

    # ── Write a 3-minute script, then present it ─────────────────────────
    talk = {"session_type": "Presentation", "deck_id": sid, "presentation_mode": "talk", "use_script": True}
    assert (await client.post("/api/live", headers=headers, json=talk)).status_code == 409   # no script yet
    r = await client.post(f"/api/sessions/{sid}/script", headers=headers, json={"minutes": 3, "style": "full"})
    assert r.status_code == 200, r.text
    assert sum(p["seconds"] for p in r.json()["slides"]) == 180
    assert (await client.get(f"/api/sessions/{sid}", headers=headers)).json()["script"]["minutes"] == 3

    r = await client.post("/api/live", headers=headers, json=talk)
    assert r.status_code == 201, r.text
    live = r.json()
    ctx = live["context"]
    assert ctx["kind"] == "talk" and "plan" not in ctx and ctx["script"] is True
    assert [s["index"] for s in ctx["slides"]] == [1, 2, 3] and all(s["key_point"] for s in ctx["slides"])
    assert all(s["script"] and s["budget_sec"] for s in ctx["slides"])

    lid = live["id"]
    times = [{"slide_index": 1, "t_sec": 0}, {"slide_index": 2, "t_sec": 6}]  # slide 3 never shown
    r = await client.post(f"/api/live/{lid}/end", headers=headers,
                          json={"duration_sec": 12, "turns": [], "client_metrics": {"slide_times": times}})
    assert r.status_code == 200, r.text
    take = _tone_wav([(0.5, False), (5, True), (1, False), (5, True), (0.5, False)])
    assert (await client.post(f"/api/live/{lid}/recording", headers=headers, files={"file": ("take.wav", take)})).status_code == 200
    assert (await client.post(f"/api/live/{lid}/analyze", headers=headers)).status_code == 202
    await tasks.wait_for_all(timeout=120)

    a = (await client.get(f"/api/live/{lid}", headers=headers)).json()
    assert a["status"] == "complete", a
    fb = a["analysis"]["content_feedback"]
    assert fb["kind"] == "slides"
    by = {r["slide_index"]: r for r in fb["slides"]}
    assert by[1]["seconds"] == 6.0 and by[2]["seconds"] == 6.0
    assert by[3]["status"] == "skipped"
    assert fb["script"]["planned_sec"] == 180 and by[3]["script_coverage"] == 0.0
    # Offline there's no speech recognition, so the shown slides have no words to judge
    assert by[1]["status"] == "silent"

    # The history list is a summary (no turns, no slide texts), and can keep one deck's attempts
    rows = (await client.get(f"/api/live?deck_id={sid}", headers=headers)).json()
    assert [r["id"] for r in rows] == [lid]
    assert rows[0]["turns"] is None and rows[0]["context"] == {"kind": "talk", "deck_id": sid, "deck_title": ctx["deck_title"]}
    assert set(rows[0]["analysis"]) == {"communication_score", "recommendations", "pillars"}
    other_deck = "00000000-0000-0000-0000-000000000000"
    assert (await client.get(f"/api/live?deck_id={other_deck}", headers=headers)).json() == []


async def test_a_deck_is_private_to_its_owner(client: httpx.AsyncClient, tmp_path: Path):
    deck = build_sample_deck(tmp_path / "deck.pptx")
    owner, other = await sign_in(client, "owner@example.com"), await sign_in(client, "other@example.com")
    sid = (await client.post("/api/sessions", headers=owner, files={"pptx": ("deck.pptx", deck.read_bytes())})).json()["session_id"]

    assert (await client.get(f"/api/sessions/{sid}", headers=owner)).status_code == 200
    assert (await client.get(f"/api/sessions/{sid}", headers=other)).status_code == 404   # as if it didn't exist
    assert (await client.get(f"/api/sessions/{sid}")).status_code == 401                  # signed out
    assert (await client.get(f"/api/sessions/{sid}/slides/1/image", headers=other)).status_code == 404
    assert (await client.delete(f"/api/sessions/{sid}", headers=other)).status_code == 404
    assert (await client.post("/api/live", headers=other, json={"session_type": "Presentation", "deck_id": sid,
                                                                "presentation_mode": "talk"})).status_code == 404
    await tasks.wait_for_all(timeout=300)
    assert (await client.get(f"/api/sessions/{sid}", headers=owner)).status_code == 200    # still there
