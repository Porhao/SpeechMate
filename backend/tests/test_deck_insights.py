"""Deck insights (before narration) and PDF decks."""

import json
import shutil
import subprocess

import httpx
import pytest

from app.config import settings
from app.database import Base, engine
from app.main import app
from app.services import deck_insights, tasks
from make_sample_deck import build as build_sample_deck

TEXTS = [
    "Time Management for Students\nWhy it matters",
    "Plan and Prioritize\n" + "\n".join(f"Point {i} about planning tomorrow's tasks carefully" for i in range(12)),
    "",
    "Protect Your Focus\nSilence notifications",
]


def test_stats_flag_text_heavy_and_textless_slides():
    stats = deck_insights.deck_stats(TEXTS)
    assert stats["slide_count"] == 4
    assert stats["text_heavy_slides"] == [2]
    assert stats["no_text_slides"] == [3]
    assert stats["estimated_minutes"] == [3.0, 6.0]


def test_rule_based_outline_and_suggestions():
    stats = deck_insights.deck_stats(TEXTS)
    out = deck_insights.rule_based_insights(TEXTS, stats, "First-year students")
    assert [s["key_point"] for s in out["slides"]][:2] == ["Time Management for Students", "Plan and Prioritize"]
    issues = " ".join(s["issue"] for s in out["suggestions"])
    assert "Text-heavy" in issues and "No readable text" in issues and "conclusion" in issues
    assert out["structure"][0] == {"section": "Opening", "slides": [1]}


class _FakeLLM:
    def __init__(self, replies):
        self.replies, self.chat, self.completions = list(replies), self, self

    async def create(self, **_):
        content = self.replies.pop(0)
        return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": content})()})()]})()


def _llm_reply(slide_numbers):
    return json.dumps({
        "summary": "A short talk on managing time as a student, from why it matters to two habits.",
        "main_message": "Plan the night before and protect your focus.",
        "audience": "Suits first-year students.",
        "structure": [{"section": "Opening", "slides": [1]}, {"section": "Habits", "slides": slide_numbers}],
        "slides": [{"slide_index": 1, "key_point": "Time management matters"}],
        "strengths": ["Clear titles"],
        "suggestions": [{"slide_index": 2, "issue": "Twelve bullets", "suggestion": "Cut to four"}],
        "likely_questions": ["How long should a focus block be?"],
    })


async def test_llm_insights_reject_nonexistent_slides_and_fill_key_points(monkeypatch):
    monkeypatch.setattr(deck_insights, "get_llm_client", lambda: _FakeLLM([_llm_reply([2, 9]), _llm_reply([2, 3, 4])]))
    out, warning = await deck_insights.analyse_deck(TEXTS, "First-year students")
    assert warning is None and out["source"] == "llm"
    assert out["main_message"].startswith("Plan the night before")
    # Every slide gets a key point, gaps filled from the slide title
    assert [s["slide_index"] for s in out["slides"]] == [1, 2, 3, 4]
    assert out["slides"][3]["key_point"] == "Protect Your Focus"


async def test_insights_fall_back_without_llm():
    out, warning = await deck_insights.analyse_deck(TEXTS, None)
    assert out["source"] == "rules" and warning is None
    assert out["stats"]["slide_count"] == 4


@pytest.mark.skipif(
    not (shutil.which(settings.libreoffice_bin) and shutil.which("pdftoppm") and shutil.which("pdftotext")
         and shutil.which(settings.ffmpeg_bin)),
    reason="needs LibreOffice (to make the test PDF), poppler and ffmpeg",
)
async def test_pdf_deck_end_to_end(tmp_path):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    deck = build_sample_deck(tmp_path / "deck.pptx")
    subprocess.run([settings.libreoffice_bin, "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(deck)],
                   check=True, capture_output=True, timeout=180)
    pdf = tmp_path / "deck.pdf"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/sessions", files={"pptx": ("deck.pdf", pdf.read_bytes())})
        assert r.status_code == 201, r.text
        sid = r.json()["session_id"]
        await tasks.wait_for_all(timeout=600)
        s = (await client.get(f"/api/sessions/{sid}")).json()
        assert s["status"] == "complete", s
        assert s["slide_count"] == 3
        ins = s["insights"]
        assert ins["stats"]["slide_count"] == 3
        assert ins["slides"][0]["key_point"].startswith("Five Strategies")  # text extracted from the PDF
        scripts = (await client.get(f"/api/sessions/{sid}/scripts")).json()["slides"]
        assert all(sl["script_text"] for sl in scripts)

    r = await httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test").post(
        "/api/sessions", files={"pptx": ("deck.docx", b"x")})
    assert r.status_code == 400
