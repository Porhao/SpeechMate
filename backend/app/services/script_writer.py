"""Script writer: a talk script for a deck, sized to the minutes the speaker has.

The time each slide gets is decided here (content-weighted), not by the LLM, so the plan always
adds up to the requested length; the LLM writes each slide's part to that word budget, from the
slide's own text and key point. Names and figures that aren't in the deck are sent back once
(practice_plans.invented_terms). Without an LLM the script is the key point plus the slide's lines.

Two styles: "full" (word for word, to practise reading then loosen) and "points" (an opening line,
2-3 talking points and a transition). The learner brief (services/learner.py) sets the level.
"""

import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.services.ai import with_retries
from app.services.learner import with_brief
from app.services.practice_plans import _llm_json, invented_terms

logger = logging.getLogger(__name__)

WPM = 130                 # a comfortable presenting pace
MAX_CHARS_PER_SLIDE = 900

SYSTEM = """You write a presentation script for a speaker to practise with, from their slides.
For each slide you get its text, the point it must land, and a word budget. Return JSON only:
{"slides": [{"slide_index": n, "text": "..."}]}
Style "full": what the speaker says on that slide, word for word, AT LEAST its "min_words" (count them; a
short script leaves the speaker with nothing to say). Fill the time by explaining each point, why it matters
and a simple example, still using only the slide's facts.
Style "points": an opening line, then 2-3 short talking points, then a one-line transition, each on its own line
starting with "- ", about a third of the word budget.
Rules: one entry per slide, in order. Use only facts on the slides: never add names, numbers or results that
aren't there. Spoken English, short sentences, plain words; explain the slide rather than read it out.
Open the first slide with a short greeting and what the talk is about; close the last slide with the main
message. Link each slide to the next."""


class _Part(BaseModel):
    slide_index: int
    text: str = Field(min_length=3, max_length=4000)


class _Script(BaseModel):
    slides: list[_Part]


def time_budget(texts: list[str], minutes: float) -> list[int]:
    """Seconds per slide, adding up to `minutes`: every slide gets a base share, plus more for more text."""
    weights = [1 + min(len(t.split()), 80) / 40 for t in texts]
    total = minutes * 60
    secs = [round(total * w / sum(weights)) for w in weights]
    secs[-1] += round(total) - sum(secs)  # rounding lands on the last slide
    return secs


def _fallback(slides: list[dict], style: str) -> list[str]:
    out = []
    for s in slides:
        lines = [ln.strip("•-– ").strip() for ln in s["text"].splitlines() if ln.strip()][1:5]
        head = s["key_point"] or s["title"]
        out.append("\n".join([f"- {head}", *(f"- {ln}" for ln in lines)]) if style == "points"
                   else " ".join([head.rstrip(".") + ".", *(ln.rstrip(".") + "." for ln in lines)]))
    return out


async def write_script(slides: list[dict], minutes: float, style: str, audience: str | None, learner: str = "") -> dict:
    """`slides`: [{"index", "title", "text", "key_point"}] in order. Returns the stored script."""
    secs = time_budget([s["text"] for s in slides], minutes)
    words = [round(sec * WPM / 60) for sec in secs]
    deck_text = " ".join(f"{s['title']} {s['text']} {s['key_point']}" for s in slides)
    n = len(slides)
    payload = {"style": style, "minutes": minutes, "audience_and_purpose": audience or "not specified", "slides": [
        {"slide_index": i, "word_budget": w, **({"min_words": w} if style == "full" else {}),
         "key_point": s["key_point"], "text": s["text"][:MAX_CHARS_PER_SLIDE]}
        for i, (s, w) in enumerate(zip(slides, words), start=1)]}

    def check(r: _Script) -> str | None:
        if sorted(p.slide_index for p in r.slides) != list(range(1, n + 1)):
            return f"Give exactly one entry for each slide 1-{n}"
        made_up = invented_terms(" ".join(p.text for p in r.slides), deck_text)
        if made_up:
            return f"These aren't on the slides, remove them: {', '.join(made_up[:8])}"
        # A full script has to fill the time: models write short, so the counts are checked
        short = [f"slide {p.slide_index} has {len(p.text.split())} words, needs about {words[p.slide_index - 1]}"
                 for p in r.slides if style == "full" and len(p.text.split()) < 0.8 * words[p.slide_index - 1]]
        return ("Too short for the time (" + "; ".join(short) + "). Expand by explaining each point more, "
                "with an example or why it matters, still using only the slides' facts") if short else None

    try:
        # Gemini sometimes answers "503 high demand" for a moment: try again before falling back
        result = await with_retries(lambda: _llm_json(with_brief(SYSTEM, learner), payload, _Script, temperature=0.5, check=check, tries=3),
                                    attempts=3, label="Script writer")
    except Exception as e:  # noqa: BLE001
        logger.error("Script writer failed: %s", e)
        result = None
    by_idx = {p.slide_index: p.text.strip() for p in result.slides if 1 <= p.slide_index <= n} if result else {}
    fallback = _fallback(slides, style)
    texts = [by_idx.get(i) or fallback[i - 1] for i in range(1, n + 1)]
    return {
        "minutes": minutes, "style": style, "wpm": WPM,
        "source": "llm" if len(by_idx) == n else "rules",
        # Names or figures still not found in the deck after the re-prompt: shown so the speaker checks them
        "unverified_terms": invented_terms(" ".join(by_idx.values()), deck_text)[:8],
        # How long it actually takes to say at WPM (the page says so when it's well off the length asked for)
        "read_sec": round(sum(len(t.split()) for t in texts) * 60 / WPM),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "slides": [{"slide_index": s["index"], "seconds": sec, "text": t} for s, sec, t in zip(slides, secs, texts)],
    }
