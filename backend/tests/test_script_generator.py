from pathlib import Path
from types import SimpleNamespace

from app.services import script_generator as sg
from app.services.ai import count_words


def test_fallback_script_uses_slide_text():
    text = sg.fallback_script(1, 3, "Time Management\n• Plan ahead\n• Focus")
    assert "Time Management" in text and "Plan ahead." in text
    assert text.startswith("Hello everyone")
    assert "Thank you" in sg.fallback_script(3, 3, "Summary\nReview weekly")


def test_fallback_script_handles_empty_slide():
    assert "slide 2" in sg.fallback_script(2, 3, "")


async def test_vlm_rewrites_when_far_outside_word_band(monkeypatch, tmp_path: Path):
    image = tmp_path / "s.png"
    image.write_bytes(b"\x89PNG fake")
    replies = ["Too short.", " ".join(["word"] * 80)]
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=replies.pop(0)))])

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(sg, "get_openai_client", lambda: fake)

    result = await sg.script_generator.generate(
        image_path=image, slide_index=2, slide_count=3, slide_text="Plan",
        requirement_prompt="for students", previous_script="Welcome everyone.",
    )
    assert result.source == "vlm"
    assert result.word_count == 80 == count_words(result.text)
    assert len(calls) == 2
    first_prompt = calls[0]["messages"][1]["content"][0]["text"]
    assert "slide 2 of 3" in first_prompt and "Welcome everyone." in first_prompt
