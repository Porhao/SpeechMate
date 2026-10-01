"""Notifications for finished work, and decks owned by the user who uploaded them."""

import shutil

import httpx
import pytest

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.services import tasks
from tests.test_e2e import _tone_wav


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "use_local_ml", False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _sign_in(client, email):
    await client.post("/api/auth/register", json={"full_name": "T", "email": email, "password": "password123"})
    tok = (await client.post("/api/auth/login", json={"email": email, "password": "password123"})).json()
    return {"Authorization": f"Bearer {tok['access_token']}"}


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_finished_live_analysis_notifies_its_owner_only(client):
    me, other = await _sign_in(client, "me@example.com"), await _sign_in(client, "other@example.com")
    assert (await client.get("/api/notifications")).status_code == 401
    assert (await client.get("/api/notifications", headers=me)).json() == {"unread": 0, "items": []}

    lid = (await client.post("/api/live", headers=me, json={"session_type": "Conversation"})).json()["id"]
    await client.post(f"/api/live/{lid}/recording", headers=me, files={"file": ("r.wav", _tone_wav([(3, True)]))})
    await client.post(f"/api/live/{lid}/analyze", headers=me)
    await tasks.wait_for_all(timeout=60)

    n = (await client.get("/api/notifications", headers=me)).json()
    assert n["unread"] == 1
    item = n["items"][0]
    assert item["kind"] == "live_analysis" and item["link"] == f"/results/{lid}" and not item["read"]
    assert (await client.get("/api/notifications", headers=other)).json()["unread"] == 0

    # Someone else can't mark it read; the owner can
    assert (await client.post(f"/api/notifications/{item['id']}/read", headers=other)).status_code == 404
    assert (await client.post(f"/api/notifications/{item['id']}/read", headers=me)).json()["read"] is True
    assert (await client.get("/api/notifications", headers=me)).json()["unread"] == 0


async def test_mark_all_read_and_deck_ownership(client):
    me, other = await _sign_in(client, "me@example.com"), await _sign_in(client, "other@example.com")
    # A deck upload that fails straight away (not a real .pptx) still notifies its owner
    r = await client.post("/api/sessions", headers=me, files={"pptx": ("broken.pptx", b"not a deck")})
    assert r.status_code == 201
    await tasks.wait_for_all(timeout=60)

    mine = (await client.get("/api/sessions", headers=me)).json()
    assert [d["original_filename"] for d in mine] == ["broken.pptx"]
    assert (await client.get("/api/sessions", headers=other)).json() == []
    assert (await client.get("/api/sessions")).json() == []  # signed out: only unowned decks

    n = (await client.get("/api/notifications", headers=me)).json()
    assert n["unread"] == 1 and n["items"][0]["kind"] == "deck_failed"
    await client.post("/api/notifications/read-all", headers=me)
    assert (await client.get("/api/notifications", headers=me)).json()["unread"] == 0
