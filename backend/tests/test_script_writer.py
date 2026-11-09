"""Script writer: the time plan adds up to the requested length; offline it falls back to the slides."""

from app.services.script_writer import time_budget, write_script
from tests.test_talk import SLIDES


def test_time_budget_adds_up_and_gives_wordier_slides_more():
    secs = time_budget(["Title", "one two three " * 20, "Thanks"], minutes=3)
    assert sum(secs) == 180
    assert secs[1] > secs[0] and all(s > 0 for s in secs)


async def test_offline_script_is_built_from_each_slide():
    full = await write_script(SLIDES, 2, "full", None)
    assert full["source"] == "rules" and full["style"] == "full"   # no LLM in tests
    assert [s["slide_index"] for s in full["slides"]] == [1, 2, 3]
    assert sum(s["seconds"] for s in full["slides"]) == 120
    assert full["slides"][0]["text"].startswith("Sleep improves memory.")
    points = await write_script(SLIDES, 2, "points", None)
    assert all(s["text"].startswith("- ") for s in points["slides"])
