"""Deck insights (Ideal Agent Stage 1b): understand the presentation before narrating it.

From the slides' text this produces a summary, the main message, the section
structure, each slide's key point, strengths, concrete suggestions and the questions
an audience is likely to ask — plus measured stats (words per slide, text-heavy or
text-less slides, an estimated talk length). The insights are shown to the presenter
before they practise, and give the script writer and the coach the whole-talk context.

Uses the configured LLM; without one (or if its answer is invalid) a deterministic
outline is built from the slide text instead. Slides are read as text only: image-only
slides are flagged rather than interpreted.
"""

import json
import logging

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.ai import count_words, get_llm_client, parse_json_object

logger = logging.getLogger(__name__)

TEXT_HEAVY_WORDS = 70
TEXT_HEAVY_LINES = 9
MAX_CHARS_PER_SLIDE = 700

SYSTEM = """You are a presentation coach reviewing a slide deck BEFORE the speaker rehearses it.
You get the text of every slide (images aren't included), measured stats, and the speaker's goal/audience.
Return JSON only:
{"summary": "3-4 sentences on what the talk covers and how it flows",
 "main_message": "the one sentence the audience should remember",
 "audience": "who this suits and whether it fits the stated audience/purpose",
 "structure": [{"section": "e.g. Opening / Problem / Method / Results / Close", "slides": [slide numbers]}],
 "slides": [{"slide_index": n, "key_point": "the point this slide must land, one sentence"}],
 "strengths": ["up to 3 specific strengths of the deck"],
 "suggestions": [{"slide_index": n or null, "issue": "specific problem", "suggestion": "concrete fix"}],
 "likely_questions": ["up to 4 questions this audience would likely ask"]}
Rules: cover every slide in "slides"; base suggestions on the actual text and stats (e.g. text-heavy slides,
missing conclusion, unclear transitions, jargon for this audience); be specific, cite slide numbers; at most 5 suggestions."""


class _Section(BaseModel):
    section: str = Field(min_length=2, max_length=60)
    slides: list[int]


class _SlidePoint(BaseModel):
    slide_index: int
    key_point: str = Field(min_length=3, max_length=300)


class _Suggestion(BaseModel):
    slide_index: int | None = None
    issue: str = Field(min_length=5, max_length=300)
    suggestion: str = Field(min_length=5, max_length=300)


class _Insights(BaseModel):
    summary: str = Field(min_length=20, max_length=900)
    main_message: str = Field(min_length=5, max_length=300)
    audience: str = Field(min_length=5, max_length=400)
    structure: list[_Section] = Field(min_length=1, max_length=8)
    slides: list[_SlidePoint]
    strengths: list[str] = Field(default_factory=list, max_length=3)
    suggestions: list[_Suggestion] = Field(default_factory=list, max_length=5)
    likely_questions: list[str] = Field(default_factory=list, max_length=4)


def _title(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def deck_stats(texts: list[str]) -> dict:
    per_slide = []
    for i, text in enumerate(texts, start=1):
        lines = [ln for ln in text.splitlines() if ln.strip()]
        words = count_words(text)
        per_slide.append({
            "slide_index": i,
            "title": _title(text)[:120],
            "words": words,
            "lines": len(lines),
            "text_heavy": words > TEXT_HEAVY_WORDS or len(lines) > TEXT_HEAVY_LINES,
            "no_text": words == 0,
        })
    n = len(texts)
    return {
        "slide_count": n,
        "total_words": sum(s["words"] for s in per_slide),
        # ~45–90 s per slide is a comfortable presenting pace
        "estimated_minutes": [round(n * 0.75, 1), round(n * 1.5, 1)],
        "text_heavy_slides": [s["slide_index"] for s in per_slide if s["text_heavy"]],
        "no_text_slides": [s["slide_index"] for s in per_slide if s["no_text"]],
        "per_slide": per_slide,
    }


def _closing_like(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in ("conclusion", "summary", "thank", "takeaway", "recap", "kesimpulan", "terima kasih", "q&a", "questions"))


def rule_based_insights(texts: list[str], stats: dict, requirement_prompt: str | None) -> dict:
    n = stats["slide_count"]
    titles = [s["title"] or f"Slide {s['slide_index']}" for s in stats["per_slide"]]
    suggestions = []
    for i in stats["text_heavy_slides"][:3]:
        s = stats["per_slide"][i - 1]
        suggestions.append({
            "slide_index": i,
            "issue": f"Text-heavy slide ({s['words']} words, {s['lines']} lines).",
            "suggestion": "Keep 3–4 short bullets on the slide and say the rest; people can't read and listen at once.",
        })
    for i in stats["no_text_slides"][:2]:
        suggestions.append({
            "slide_index": i,
            "issue": "No readable text on this slide (image or chart only).",
            "suggestion": "Prepare one sentence that tells the audience what to notice in the visual.",
        })
    if n > 2 and not _closing_like(titles[-1]):
        suggestions.append({
            "slide_index": n,
            "issue": "The deck doesn't end on a conclusion or summary slide.",
            "suggestion": "Close by restating your main message and one takeaway or next step.",
        })
    if n >= 3:
        structure = [{"section": "Opening", "slides": [1]}, {"section": "Body", "slides": list(range(2, n))},
                     {"section": "Close", "slides": [n]}]
    else:
        structure = [{"section": "Talk", "slides": list(range(1, n + 1))}]
    return {
        "summary": f"A {n}-slide presentation covering: " + "; ".join(titles[:8]) + ("…" if n > 8 else "."),
        "main_message": titles[0] if titles else "",
        "audience": requirement_prompt or "Audience not specified.",
        "structure": structure,
        "slides": [{"slide_index": i, "key_point": t} for i, t in enumerate(titles, start=1)],
        "strengths": [],
        "suggestions": suggestions[:5],
        "likely_questions": [],
    }


async def analyse_deck(texts: list[str], requirement_prompt: str | None) -> tuple[dict, str | None]:
    """Returns (insights, warning). Insights always include `stats` and `source` (llm | rules)."""
    stats = deck_stats(texts)
    client = get_llm_client()
    if client is None or not any(t.strip() for t in texts):
        reason = None if client is None else "The deck has no readable text, so insights are limited to its structure."
        return {**rule_based_insights(texts, stats, requirement_prompt), "stats": stats, "source": "rules"}, reason

    n = len(texts)
    payload = {
        "speaker_goal_and_audience": requirement_prompt or "not specified",
        "stats": {k: v for k, v in stats.items() if k != "per_slide"},
        "slides": [{"slide_index": i, "text": t[:MAX_CHARS_PER_SLIDE]} for i, t in enumerate(texts, start=1)],
    }
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
    try:
        for _ in range(2):
            resp = await client.chat.completions.create(
                model=settings.llm_model, messages=messages, response_format={"type": "json_object"}, temperature=0.3
            )
            content = resp.choices[0].message.content or ""
            try:
                data = _Insights.model_validate(parse_json_object(content))
                bad = sorted({i for s in data.structure for i in s.slides if not 1 <= i <= n}
                             | {s.slide_index for s in data.slides if not 1 <= s.slide_index <= n})
                if bad:
                    raise ValueError(f"slide numbers {bad} don't exist; the deck has slides 1-{n}")
                out = data.model_dump()
                # Make sure every slide has a key point (fill gaps from its title)
                have = {s["slide_index"] for s in out["slides"]}
                for s in stats["per_slide"]:
                    if s["slide_index"] not in have:
                        out["slides"].append({"slide_index": s["slide_index"], "key_point": s["title"] or "—"})
                out["slides"].sort(key=lambda s: s["slide_index"])
                return {**out, "stats": stats, "source": "llm"}, None
            except (ValueError, ValidationError) as e:
                logger.warning("Deck insights JSON invalid, re-prompting: %s", e)
                messages += [{"role": "assistant", "content": content},
                             {"role": "user", "content": f"That was invalid: {e}. Return corrected JSON only."}]
        warning = "The AI deck analysis returned invalid results twice; showing a text-based outline instead."
    except Exception as e:  # noqa: BLE001
        logger.error("Deck insights failed: %s", e)
        warning = f"AI deck analysis failed ({e}); showing a text-based outline instead."
    return {**rule_based_insights(texts, stats, requirement_prompt), "stats": stats, "source": "rules"}, warning


def script_context(insights: dict | None, slide_index: int) -> str | None:
    """Whole-talk context for one slide's narration."""
    if not insights:
        return None
    parts = [f"Main message of the whole talk: {insights.get('main_message', '')}"]
    sections = insights.get("structure") or []
    for s in sections:
        if slide_index in (s.get("slides") or []):
            parts.append(f"This slide is in the \"{s.get('section')}\" part of the talk.")
    point = next((s["key_point"] for s in insights.get("slides", []) if s.get("slide_index") == slide_index), None)
    if point:
        parts.append(f"The point this slide must land: {point}")
    return "\n".join(parts)


def coach_context(insights: dict | None) -> str:
    if not insights:
        return ""
    return (
        f"Deck summary: {insights.get('summary', '')}\n"
        f"Main message: {insights.get('main_message', '')}\n"
        "Slide key points: " + "; ".join(f"[{s['slide_index']}] {s['key_point']}" for s in insights.get("slides", []))
    )
