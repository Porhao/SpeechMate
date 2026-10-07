"""Presentation talk: words are split by when each slide was on screen, then checked against it."""

from app.services.live.talk import split_by_slide, talk_feedback

SLIDES = [
    {"index": 1, "title": "Why sleep matters", "text": "Sleep improves memory and focus", "key_point": "Sleep improves memory"},
    {"index": 2, "title": "Our survey", "text": "120 students surveyed about sleep hours", "key_point": "Most students sleep under six hours"},
    {"index": 3, "title": "Recommendations", "text": "Fixed bedtime, no phones", "key_point": "Keep a fixed bedtime"},
]


def _words(text: str, start: float, step: float = 0.5) -> list[dict]:
    return [{"word": w, "start": start + i * step, "end": start + i * step + 0.3} for i, w in enumerate(text.split())]


def test_words_follow_the_slide_on_screen_including_revisits():
    words = _words("hello sleep improves memory", 0) + _words("we surveyed students", 10) + _words("back to memory", 20)
    times = [{"slide_index": 1, "t_sec": 0.5}, {"slide_index": 2, "t_sec": 8}, {"slide_index": 1, "t_sec": 18}]
    parts = split_by_slide(words, times, duration_sec=25)
    assert parts[1]["said"] == "hello sleep improves memory back to memory"  # before the first mark counts too
    assert parts[2]["said"] == "we surveyed students"
    assert parts[1]["seconds"] == 15.0 and parts[2]["seconds"] == 10.0     # 0–8 + 18–25, and 8–18
    assert split_by_slide(words, None, 25) == {}


async def test_each_slide_is_judged_against_what_was_said_while_it_showed():
    words = (_words("sleep improves memory and focus for everyone", 0)
             + _words("um so yeah", 30))                      # slide 2: on screen, nothing about it
    times = [{"slide_index": 1, "t_sec": 0}, {"slide_index": 2, "t_sec": 25}]
    fb = await talk_feedback({"slides": SLIDES}, words, times, duration_sec=40)
    by = {r["slide_index"]: r for r in fb["slides"]}
    assert fb["kind"] == "slides" and fb["source"] == "rules"   # no LLM in tests
    assert by[1]["status"] == "covered" and by[1]["seconds"] == 25.0
    assert by[2]["status"] == "missed" and "students" in by[2]["missed_terms"]
    assert by[3]["status"] == "skipped" and by[3]["coverage"] is None
    assert "2 of 3 slides" in fb["summary"]
    assert await talk_feedback({"slides": SLIDES}, words, [], 40) is None   # no slide timings → nothing to judge
