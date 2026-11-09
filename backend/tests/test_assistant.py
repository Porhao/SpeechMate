"""Mate: answers need sign-in; offline it points to the right pages instead of failing."""

import httpx

from app.database import Base, engine
from app.main import app
from tests.conftest import sign_in


async def test_mate_replies_offline_and_needs_sign_in():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        msg = {"messages": [{"role": "user", "text": "What does my pace score mean?"}], "page": "/progress"}
        assert (await c.post("/api/assistant/chat", json=msg)).status_code == 401
        headers = await sign_in(c, "mate@example.com")
        r = await c.post("/api/assistant/chat", json=msg, headers=headers)
        assert r.status_code == 200 and "/methodology" in r.json()["reply"]   # no LLM in tests
        assert (await c.post("/api/assistant/chat", json={"messages": []}, headers=headers)).status_code == 422
