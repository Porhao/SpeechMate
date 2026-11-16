"""Judging what was said after a session (not how): each interview / Q&A answer against its plan,
or language corrections for a conversation. Rule-based when there is no LLM."""

import logging
import re

from pydantic import BaseModel, Field

from app.services.ai import llm_json
from app.services.learner import with_brief
from app.services.plans import MAX_PLAN_QUESTIONS
from app.services.text import count_words, invented_terms

logger = logging.getLogger(__name__)


def pair_turns(turns: list[dict]) -> list[dict]:
    """[{question, answer}] — each AI turn with the user's reply that followed it."""
    pairs, current = [], None
    for t in turns or []:
        text = (t.get("text") or "").strip()
        if not text:
            continue
        if t.get("role") == "assistant":
            if current and current["answer"]:
                pairs.append(current)
            current = {"question": text, "answer": ""}
        elif current is not None:
            current["answer"] = (current["answer"] + " " + text).strip()
    if current and current["answer"]:
        pairs.append(current)
    return pairs


class _AnswerFeedback(BaseModel):
    question: str
    relevance: int = Field(ge=1, le=5)
    structure: int = Field(ge=1, le=5)
    specificity: int = Field(ge=1, le=5)
    went_well: str = Field(default="", max_length=300)  # a small model sometimes skips it: keep the rest
    improve: str = Field(min_length=3, max_length=300)
    stronger_answer: str = Field(min_length=10, max_length=600)


class _AnswersReport(BaseModel):
    summary: str = Field(min_length=10, max_length=600)
    answers: list[_AnswerFeedback] = Field(max_length=MAX_PLAN_QUESTIONS + 4)


class _Correction(BaseModel):
    said: str = Field(min_length=1, max_length=300)
    better: str = Field(min_length=1, max_length=300)
    why: str = Field(default="", max_length=300)  # a small model sometimes skips it: keep the correction


class _ConversationReport(BaseModel):
    summary: str = Field(min_length=10, max_length=600)
    corrections: list[_Correction] = Field(default_factory=list, max_length=6)
    tips: list[str] = Field(default_factory=list, max_length=3)


ANSWERS_SYSTEM = """You are a {who} giving feedback on each answer after the session.
For every question-answer pair, rate 1-5: relevance (did it answer the question asked), structure ({structure}),
specificity (concrete examples, numbers, names vs. generic). Say what went well and the one thing to improve,
and write a short stronger version of the answer using ONLY facts the candidate actually said (plus {extra}):
never add tools, companies, places, numbers or results they didn't mention; where a detail is missing, write a
placeholder like "<the result>" so they know to fill it in.
Write for a language learner: plain everyday words, short sentences, no jargon. In "went_well" and "improve",
quote a few of the candidate's own words so they can see exactly which part you mean, and make "improve" one
concrete action ("Start with the result: 'We cut errors by half'"), not general advice ("be more specific").
Be encouraging. Then a 2-sentence overall summary.
Return JSON only, every field filled:
{{"summary": "...", "answers": [{{"question": "...", "relevance": 1-5, "structure": 1-5, "specificity": 1-5,
"went_well": "...", "improve": "...", "stronger_answer": "..."}}]}}"""

CONVERSATION_SYSTEM = """You are a friendly English communication coach for a Malaysian learner. From the learner's turns in
a casual conversation, pick up to 5 real grammar or word-choice issues worth fixing (quote what they said, give the natural
version, explain in one short plain sentence why it's better). Malaysian English expressions and particles like "lah" are
fine — only correct things that would confuse a listener or sound wrong in a formal setting. Add up to 3 tips about keeping a
conversation going, each tied to something they actually said ("When asked about your week you said 'okay only' — add one
detail, like what you did on Saturday"). Then a 2-sentence summary starting with something they did well. Plain everyday
words, no grammar jargon.
Return JSON only, every field filled:
{"summary": "...", "corrections": [{"said": "...", "better": "...", "why": "..."}], "tips": ["..."]}"""

_STAR_CUES = {
    "situation": ("when i", "at my", "during", "in my", "last year", "once", "while i"),
    "action": ("i decided", "i did", "i led", "i built", "i talked", "i worked", "i organised", "i organized", "i created", "i took"),
    "result": ("as a result", "in the end", "result", "so we", "which led", "improved", "increased", "reduced", "%", "percent"),
}


def _rule_answer(pair: dict, look_for: list[str] | None) -> dict:
    answer = pair["answer"]
    words = count_words(answer)
    low = answer.lower()
    star = sum(any(c in low for c in cues) for cues in _STAR_CUES.values())
    q_terms = {w for w in re.findall(r"[a-z]{5,}", pair["question"].lower())}
    overlap = sum(1 for w in q_terms if w in low)
    numbers = bool(re.search(r"\d", answer))
    relevance = 4 if overlap >= 2 else 3 if overlap == 1 or words > 40 else 2
    structure = min(5, 2 + star)
    specificity = min(5, 2 + numbers + (words > 60) + (star >= 2))
    improve = ("Give a concrete example: the situation, what YOU did, and the result." if star < 2
               else "Add a number or outcome to make the result memorable." if not numbers
               else "Tighten it: lead with your main point in the first sentence.")
    if words < 25:
        improve = f"Your answer was short ({words} words). Aim for 60-120 words with one concrete example."
    return {
        "question": pair["question"], "relevance": relevance, "structure": structure, "specificity": specificity,
        "went_well": f"You answered in {words} words" + (" with a concrete number" if numbers else "") + ".",
        "improve": improve,
        "stronger_answer": "Structure it as: situation → your actions → the result"
                           + (f", covering: {', '.join(look_for[:3])}." if look_for else "."),
    }


async def _ask(system: str, payload: dict, model, check=None):
    """The LLM's report, or None (no LLM, or it failed: the caller gives the rule-based feedback)."""
    try:
        return await llm_json(system, payload, model, temperature=0.3, check=check)
    except Exception as e:  # noqa: BLE001 — provider error
        logger.warning("Content feedback LLM call failed, using rules: %s", e)
        return None


async def content_feedback(session_type: str, context: dict | None, turns: list[dict] | None, learner: str = "") -> dict | None:
    """Judge what was said (not how): per-answer for Interview / Presentation Q&A, corrections for Conversation.
    `learner` (services/learner.py) sets the depth and tone the learner asked for."""
    pairs = pair_turns(turns or [])
    if not pairs:
        return None
    if session_type in ("Interview", "Presentation"):
        plan_q = {q["question"]: q for q in ((context or {}).get("plan") or {}).get("questions", [])}
        # Show the planned question, not the whole spoken turn ("Thanks, that's clear. <question>")
        for p in pairs:
            p["question"] = next((q for q in plan_q if q in p["question"]), p["question"])
        if session_type == "Interview":
            setup = (context or {}).get("setup", {})
            who = f"hiring manager for a {setup.get('level', '')} {setup.get('position', '')} role".strip()
            system = ANSWERS_SYSTEM.format(who=who, structure="STAR: situation, task, action, result",
                                           extra="their resume facts if given")
            payload = {"setup": setup, "resume_excerpt": ((context or {}).get("resume_text") or "")[:1500],
                       "plan": list(plan_q.values()), "pairs": pairs}
        else:
            system = ANSWERS_SYSTEM.format(who="presentation coach reviewing the Q&A",
                                           structure="direct answer first, then reason/evidence",
                                           extra="facts from the deck summary")
            payload = {"deck_summary": (context or {}).get("deck_summary", ""), "plan": list(plan_q.values()), "pairs": pairs}
        # What a stronger answer may draw on: that answer, plus the resume / background / deck
        known = " ".join([(context or {}).get("resume_text") or "", ((context or {}).get("setup") or {}).get("background") or "",
                          (context or {}).get("deck_summary") or ""])

        def facts_for(i: int) -> str:
            return f"{pairs[i]['answer']} {pairs[i]['question']} {known}" if i < len(pairs) else known

        def check(r: _AnswersReport) -> str | None:
            bad = sorted({t for i, a in enumerate(r.answers) for t in invented_terms(a.stronger_answer, facts_for(i))})
            return f"Your stronger answers invent details the candidate never said: {', '.join(bad)}" if bad else None

        report = await _ask(with_brief(system, learner), payload, _AnswersReport, check=check)
        if report:
            for i, a in enumerate(report.answers):  # still inventing after the re-prompt: don't show a made-up answer
                if invented_terms(a.stronger_answer, facts_for(i)):
                    a.stronger_answer = ("Lead with your main point, then the situation, what you did and the result, "
                                         "using your own details.")
            out = report.model_dump()
            for i, a in enumerate(out["answers"]):  # the learner's own words, shown next to the feedback
                a["answer"] = pairs[i]["answer"] if i < len(pairs) else ""
            return {"kind": "answers", **out, "source": "llm"}
        answers = [{**_rule_answer(p, (plan_q.get(p["question"]) or {}).get("look_for")), "answer": p["answer"]} for p in pairs]
        avg = sum(a["structure"] for a in answers) / len(answers)
        return {"kind": "answers", "source": "rules", "answers": answers,
                "summary": f"You answered {len(answers)} question(s). "
                           + ("Your answers had clear structure — now add more specifics." if avg >= 4
                              else "Use situation → action → result to give your answers more structure.")}
    # Conversation
    report = await _ask(with_brief(CONVERSATION_SYSTEM, learner), {"learner_turns": [p["answer"] for p in pairs],
                                                                 "partner_turns": [p["question"] for p in pairs]}, _ConversationReport)
    if report:
        return {"kind": "conversation", **report.model_dump(), "source": "llm"}
    avg_words = sum(count_words(p["answer"]) for p in pairs) / len(pairs)
    asked_back = sum("?" in p["answer"] for p in pairs)
    tips = []
    if avg_words < 15:
        tips.append(f"Your replies averaged {avg_words:.0f} words — add a detail or a reason to each answer.")
    if asked_back == 0:
        tips.append("Ask a question back now and then — it keeps a conversation two-way.")
    return {"kind": "conversation", "source": "rules", "corrections": [], "tips": tips,
            "summary": f"You kept the conversation going for {len(pairs)} exchange(s), averaging {avg_words:.0f} words per reply."}
