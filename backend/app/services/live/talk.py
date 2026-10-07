"""Presentation talk: did what the presenter said match each slide?

The browser records when each slide was put on screen ({slide_index, t_sec} from the start of
the recording). The transcript's word timings are split at those moments, so every slide gets
the words spoken while it was showing. Each slide is then judged two ways:

- rules (always): how many of the slide's key words (its key point, weighted double, title and
  text) the presenter actually said, and how long they spent on it;
- the local LLM (when available): a 1-5 alignment score, what they covered (quoting them), the
  most important thing they left out, and one tip.
"""

from pydantic import BaseModel, Field

from app.services.coach.metrics import script_coverage

# Presenters paraphrase slides, so keyword coverage runs lower than against a script
COVERED, PARTLY = 0.4, 0.2

TALK_SYSTEM = """You are a presentation coach. For each slide you get its title, its text, the point it must land,
and what the presenter actually said while it was on screen. Judge whether the talk matched the slide:
"alignment" 1-5 (5 = explained the slide's point clearly in their own words; 3 = touched on it; 1 = talked about
something else or skipped it), "covered": one plain sentence on what they explained, quoting a few of their words,
"missing": the most important thing on the slide they left out ("" if nothing), "tip": one concrete thing to say
or do on this slide next time. Judge only from what they said; don't invent. Plain everyday words, no jargon.
Then a 2-sentence "summary" of the whole talk starting with something they did well.
Return JSON only, every field filled:
{"summary": "...", "slides": [{"slide_index": n, "alignment": 1-5, "covered": "...", "missing": "...", "tip": "..."}]}"""


class _SlideJudgement(BaseModel):
    slide_index: int
    alignment: int = Field(ge=1, le=5)
    covered: str = Field(default="", max_length=400)
    missing: str = Field(default="", max_length=400)
    tip: str = Field(default="", max_length=400)


class _TalkReport(BaseModel):
    summary: str = Field(min_length=10, max_length=700)
    slides: list[_SlideJudgement]


def split_by_slide(words: list[dict], slide_times: list[dict] | None, duration_sec: float) -> dict[int, dict]:
    """{slide_index: {"seconds", "said"}}: the time each slide was on screen (summed over visits)
    and the words whose start fell inside those spans."""
    marks = sorted((m for m in slide_times or [] if isinstance(m, dict) and "slide_index" in m and "t_sec" in m),
                   key=lambda m: m["t_sec"])
    if not marks:
        return {}
    spans = [(int(m["slide_index"]), max(0.0, float(m["t_sec"])),
              float(marks[i + 1]["t_sec"]) if i + 1 < len(marks) else max(duration_sec, float(m["t_sec"])))
             for i, m in enumerate(marks)]
    spans[0] = (spans[0][0], 0.0, spans[0][2])  # anything said before the first mark belongs to the first slide
    out: dict[int, dict] = {}
    for idx, start, end in spans:
        part = out.setdefault(idx, {"seconds": 0.0, "words": []})
        part["seconds"] += max(0.0, end - start)
        part["words"] += [w["word"] for w in words if start <= w.get("start", -1) < end]
    return {i: {"seconds": round(p["seconds"], 1), "said": " ".join(p["words"]).strip()} for i, p in out.items()}


def _rule_rows(slides: list[dict], parts: dict[int, dict]) -> list[dict]:
    rows = []
    for s in slides:
        idx = s["index"]
        part = parts.get(idx)
        reference = f"{s.get('key_point', '')} {s.get('key_point', '')} {s.get('title', '')} {s.get('text', '')}"
        if part is None:
            status, coverage, missed = "skipped", None, []
        elif not part["said"]:
            status, coverage, missed = "silent", 0.0, []
        else:
            coverage, missed = script_coverage(part["said"], reference)
            status = ("covered" if coverage is None or coverage >= COVERED
                      else "partly" if coverage >= PARTLY else "missed")
        rows.append({
            "slide_index": idx, "title": s.get("title", ""), "key_point": s.get("key_point", ""),
            "seconds": part["seconds"] if part else 0.0, "said": (part["said"] if part else "")[:600],
            "coverage": coverage, "missed_terms": missed[:5], "status": status,
            "alignment": None, "covered": "", "missing": "", "tip": "",
        })
    return rows


def _rule_summary(rows: list[dict]) -> str:
    shown = [r for r in rows if r["status"] != "skipped"]
    good = [r for r in shown if r["status"] == "covered"]
    weak = [r for r in shown if r["status"] in ("missed", "silent")]
    text = f"You presented {len(shown)} of {len(rows)} slides and clearly covered {len(good)}."
    if weak:
        text += f" Slide{'s' if len(weak) > 1 else ''} {', '.join(str(r['slide_index']) for r in weak[:4])} need more about what's on them."
    return text


async def talk_feedback(context: dict, words: list[dict], slide_times: list[dict] | None, duration_sec: float) -> dict | None:
    """Per-slide alignment of the talk with the deck (`kind: "slides"`), or None without slides or timings."""
    from app.services.practice_plans import _llm_json  # validated, re-prompted JSON from the local LLM

    slides = context.get("slides") or []
    parts = split_by_slide(words, slide_times, duration_sec)
    if not slides or not parts:
        return None
    rows = _rule_rows(slides, parts)
    spoken = [r for r in rows if r["said"]]
    report = None
    if spoken:
        payload = {"deck_title": context.get("deck_title", ""), "slides": [
            {"slide_index": r["slide_index"], "title": r["title"], "key_point": r["key_point"],
             "slide_text": next((s.get("text", "") for s in slides if s["index"] == r["slide_index"]), "")[:600],
             "presenter_said": r["said"]} for r in spoken]}
        report = await _llm_json(TALK_SYSTEM, payload, _TalkReport, temperature=0.3)
    if report:
        by_idx = {j.slide_index: j for j in report.slides}
        for r in rows:
            if (j := by_idx.get(r["slide_index"])) and r["said"]:
                r.update(alignment=j.alignment, covered=j.covered, missing=j.missing, tip=j.tip)
    return {
        "kind": "slides", "source": "llm" if report else "rules",
        "summary": report.summary if report else _rule_summary(rows),
        "slides": rows,
        "total_sec": round(sum(r["seconds"] for r in rows), 1),
    }
