"""PDPA controls: cloud-processing consent, recording retention, data export, account deletion."""

import json
import shutil

import httpx
import pytest

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.services import tasks
from app.services.storage import storage_service
from tests.test_e2e import _tone_wav


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "use_local_ml", False)
    monkeypatch.setattr(settings, "require_cloud_consent", True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _sign_in(client, email="nur@example.com", password="correct-horse"):
    await client.post("/api/auth/register", json={"full_name": "Nur", "email": email, "password": password})
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_cloud_processing_needs_consent_and_it_can_be_withdrawn(client):
    h = await _sign_in(client)
    assert (await client.get("/api/users/profile", headers=h)).json()["cloud_consent_at"] is None
    for method, path, body in (("post", "/api/live", {"session_type": "Conversation"}),
                               ("post", "/api/interview/plan", {"position": "Nurse"})):
        r = await getattr(client, method)(path, headers=h, json=body)
        assert r.status_code == 403 and r.json()["detail"] == "cloud_consent_required"
    r = await client.post("/api/sessions", headers=h, files={"pptx": ("d.pdf", b"%PDF-1.4")})
    assert r.status_code == 403

    r = await client.post("/api/users/me/consent", headers=h, json={"accept": True})
    assert r.json()["cloud_consent_at"] is not None
    assert (await client.post("/api/live", headers=h, json={"session_type": "Conversation"})).status_code == 201

    await client.post("/api/users/me/consent", headers=h, json={"accept": False})
    assert (await client.post("/api/live", headers=h, json={"session_type": "Conversation"})).status_code == 403


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_recording_deleted_after_analysis_unless_kept(client):
    h = await _sign_in(client)
    await client.post("/api/users/me/consent", headers=h, json={"accept": True})

    async def analysed() -> dict:
        lid = (await client.post("/api/live", headers=h, json={"session_type": "Conversation"})).json()["id"]
        await client.post(f"/api/live/{lid}/recording", headers=h, files={"file": ("r.wav", _tone_wav([(3, True), (1, False), (3, True)]))})
        await client.post(f"/api/live/{lid}/analyze", headers=h)
        await tasks.wait_for_all(timeout=60)
        return (await client.get(f"/api/live/{lid}", headers=h)).json()

    s = await analysed()
    assert s["status"] == "complete" and not s["has_recording"]
    assert not storage_service.get_absolute_path(f"live/{s['id']}").exists()

    r = await client.put("/api/users/profile", headers=h, json={"keep_recordings": True})
    assert r.json()["keep_recordings"] is True
    s = await analysed()
    assert s["status"] == "complete" and s["has_recording"]


@pytest.mark.skipif(shutil.which(settings.ffmpeg_bin) is None, reason="ffmpeg is required")
async def test_export_and_delete_account(client):
    h = await _sign_in(client)
    other = await _sign_in(client, "other@example.com")
    await client.post("/api/users/me/consent", headers=h, json={"accept": True})
    await client.put("/api/users/profile", headers=h, json={"keep_recordings": True})
    lid = (await client.post("/api/live", headers=h, json={"session_type": "Conversation", "topic": "my week"})).json()["id"]
    await client.post(f"/api/live/{lid}/recording", headers=h, files={"file": ("r.wav", _tone_wav([(3, True)]))})

    r = await client.get("/api/users/me/export", headers=h)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = json.loads(r.text)
    assert data["profile"]["email"] == "nur@example.com" and "password_hash" not in data["profile"]
    assert [s["id"] for s in data["practice_sessions"]] == [lid]
    assert "recording_storage_path" not in data["practice_sessions"][0]

    folder = storage_service.get_absolute_path(f"live/{lid}")
    assert folder.exists()
    assert (await client.request("DELETE", "/api/users/me", headers=h, json={"password": "wrong"})).status_code == 403
    assert (await client.request("DELETE", "/api/users/me", headers=h, json={"password": "correct-horse"})).status_code == 204
    assert not folder.exists()
    assert (await client.get("/api/users/profile", headers=h)).status_code == 401
    assert (await client.post("/api/auth/login", json={"email": "nur@example.com", "password": "correct-horse"})).status_code == 401
    assert (await client.get("/api/users/profile", headers=other)).status_code == 200   # nobody else touched
