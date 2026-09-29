"""Malaysian TTS text preparation and the narrator-voice API (no model needed)."""

import httpx
import pytest

from app.database import Base, engine
from app.main import app
from app.services import malaysian_tts


def test_numbers_are_spelled_out():
    assert malaysian_tts.normalize("Top 3 tasks, 25% faster, 1200 users") == (
        "Top three tasks, twenty five percent faster, one thousand two hundred users"
    )


def test_chunks_fit_one_generation():
    text = (
        "Selamat pagi semua. " + "This is a deliberately long sentence that keeps going, and going, and going " * 4
        + "until it ends."
    )
    chunks = malaysian_tts.chunk_text(text)
    assert chunks[0] == "Selamat pagi semua."
    assert all(len(c) <= malaysian_tts.CHUNK_MAX_CHARS for c in chunks)
    # Nothing dropped
    assert " ".join(chunks).replace(" ", "") == malaysian_tts.normalize(text).replace(" ", "")


def test_empty_text_has_no_chunks():
    assert malaysian_tts.chunk_text(" ... ") == []


@pytest.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_narrator_voices_endpoint(client: httpx.AsyncClient):
    r = (await client.get("/api/narrator-voices")).json()
    assert r["default"] == "husein"
    assert {v["id"] for v in r["voices"]} >= {"husein", "idayu", "haqkiem"}
    assert r["available"] is False  # USE_LOCAL_ML=false in tests


async def test_unknown_narrator_voice_is_rejected(client: httpx.AsyncClient):
    r = await client.post(
        "/api/sessions",
        files={"pptx": ("deck.pptx", b"x")},
        data={"narrator_voice": "not-a-voice"},
    )
    assert r.status_code == 400
    assert "narrator_voice" in r.json()["detail"]
