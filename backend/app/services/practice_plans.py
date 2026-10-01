"""Curated practice for the three functions: Conversation, Mock interview, Presentation Q&A.

- Interview: from the candidate's setup (position, company, level, interview type,
  background, job description, optional resume) build a question plan — what each
  question assesses and what a strong answer contains.
- Presentation Q&A: from a deck's insights build the questions an audience would ask.
- During the session the AI partner follows the plan (one question at a time, one
  follow-up when an answer is thin).
- After the session, judge the *content* of each answer against the plan (interview /
  Q&A) or give language corrections (conversation).

Every LLM step has a rule-based fallback so the feature works without a model.
"""

import json
import logging
import re
import subprocess
import zipfile
from io import BytesIO

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.services.ai import count_words, get_llm_client, parse_json_object

logger = logging.getLogger(__name__)

MAX_RESUME_CHARS = 8000
MAX_PLAN_QUESTIONS = 8


# ── Resume text ─────────────────────────────────────────────────────────────

def extract_resume_text(data: bytes, filename: str) -> str:
    """Plain text from a PDF, DOCX or TXT resume (best effort, truncated)."""
    name = filename.lower()
    text = ""
    if name.endswith(".pdf"):
        try:
            text = subprocess.run(["pdftotext", "-layout", "-", "-"], input=data, capture_output=True,
                                  timeout=60, check=True).stdout.decode("utf-8", "replace")
        except (OSError, subprocess.SubprocessError) as e:
            raise ValueError(f"Couldn't read the PDF ({e})") from e
    elif name.endswith(".docx"):
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
        except (zipfile.BadZipFile, KeyError) as e:
            raise ValueError("That doesn't look like a valid .docx file") from e
        xml = re.sub(r"</w:p>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", xml)
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", "replace")
    else:
        raise ValueError("Upload the resume as PDF, DOCX or TXT")
    text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
    if not text:
        raise ValueError("No text could be read from the resume (is it a scanned image?)")
    return text[:MAX_RESUME_CHARS]


# ── Plans ───────────────────────────────────────────────────────────────────

class _PlanQuestion(BaseModel):
    question: str = Field(min_length=8, max_length=400)
    assesses: str = Field(min_length=3, max_length=200)
    look_for: list[str] = Field(min_length=1, max_length=5)
    slide_index: int | None = None


class _Plan(BaseModel):
    greeting: str = Field(min_length=10, max_length=600)
    questions: list[_PlanQuestion] = Field(min_length=3, max_length=MAX_PLAN_QUESTIONS)


def _compose_intro(greeting: str, first_question: str, name: str | None) -> str:
    """The spoken opening: the model's greeting (placeholders filled, any question in it dropped)
    followed by planned question 1 word-for-word, so the plan and the conversation never drift."""
    greeting = re.sub(r"\[[^\]]*\]", name or "", greeting).lstrip(".…,;: ")
    greeting = re.sub(r"\s+([,.!])", r"\1", re.sub(r"\s{2,}", " ", greeting)).strip()
    sentences = re.split(r"(?<=[.!?])\s+", greeting)
    keep = [x for x in sentences if x and not x.endswith("?")
            and not re.search(r"\b(tell me|let's start|opener|first question)\b", x, re.I)]
    return " ".join(keep[:2] + [first_question]).strip()


async def _llm_json(system: str, payload: dict, model_cls, temperature: float = 0.4, check=None):
    """JSON from the LLM, validated against `model_cls` (and `check(result) -> error | None`),
    re-prompted once with the problem. A result that still fails `check` is returned as is
    (the caller repairs it); one that fails validation gives None (the caller falls back)."""
    client = get_llm_client()
    if client is None:
        return None
    messages = [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
    result = None
    for _ in range(2):
        resp = await client.chat.completions.create(
            model=settings.llm_model, messages=messages, response_format={"type": "json_object"}, temperature=temperature
        )
        content = resp.choices[0].message.content or ""
        try:
            result = model_cls.model_validate(parse_json_object(content))
            problem = check(result) if check else None
        except (ValueError, ValidationError) as e:
            problem = f"That was invalid: {e}"
        if not problem:
            return result
        logger.warning("LLM output rejected, re-prompting: %s", problem)
        messages += [{"role": "assistant", "content": content},
                     {"role": "user", "content": f"{problem}. Return corrected JSON only."}]
    return result


def invented_terms(text: str, source: str) -> list[str]:
    """Names and numbers in `text` that never appear in `source`: capitalised words that
    don't start a sentence (tools, companies, places) and any figure."""
    known = {w.lower() for w in re.findall(r"[\w']+", source)}
    found = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = re.findall(r"[\w'%]+", sentence)
        for i, w in enumerate(words):
            name = i > 0 and w[:1].isupper() and len(w) > 2 and w != "I"
            if (name or any(ch.isdigit() for ch in w)) and w.lower().rstrip("%") not in known and w.lower() not in known:
                found.append(w)
    return list(dict.fromkeys(found))


INTERVIEW_SYSTEM = """You are an experienced hiring manager preparing a realistic mock interview.
From the candidate's setup (and resume, if given) write a plan of 6-8 questions in the order you'd ask them:
start with a warm opener ("tell me about yourself" tailored to the role), then questions that test what THIS
role needs at THIS level, referencing the candidate's real experience/resume where useful, and finish with
"Do you have any questions for us?". Match the interview type (behavioural → STAR situations; technical →
role-specific problem solving; mixed → both). For each question say what it assesses and 2-4 things a strong
answer contains. Each "question" is exactly what you'd say aloud: no labels, categories or numbering.
Write a 1-2 sentence spoken greeting as the interviewer (your name is Alex; greet the candidate
by name if given; mention the role and company) WITHOUT asking any question; the first question follows it.
Return JSON only: {"greeting": "...", "questions": [{"question": "...", "assesses": "...", "look_for": ["..."]}]}"""

QA_SYSTEM = """You are an audience member preparing questions for the Q&A after a presentation.
From the deck's summary, structure, key points and likely questions, write 5-6 questions this audience would really
ask: clarifying a key point, challenging a claim, asking for an example or evidence, asking about limitations or
next steps. Tie each to the slide it's about (slide_index, or null for the whole talk). For each say what it
assesses and 2-4 things a strong answer contains (grounded in the deck). Write a 1-2 sentence spoken greeting as
the session moderator thanking the presenter and opening the floor, WITHOUT asking any question.
Return JSON only: {"greeting": "...", "questions": [{"question": "...", "slide_index": n|null, "assesses": "...", "look_for": ["..."]}]}"""

_QUESTION_BANK = {
    "behavioural": [
        ("Tell me about yourself and why you're interested in this {position} role.", "Motivation and fit", ["Relevant background", "Why this role", "Kept to ~1-2 minutes"]),
        ("Describe a time you worked in a team that disagreed. What did you do?", "Teamwork and conflict", ["Specific situation", "Your actions", "Outcome"]),
        ("Tell me about a challenge you faced and how you overcame it.", "Problem solving and resilience", ["Situation and task", "Actions you took", "Measurable result"]),
        ("Give an example of a time you had to learn something quickly.", "Learning agility", ["Context", "How you learned", "What you delivered"]),
        ("Tell me about a mistake you made and what you learned.", "Self-awareness", ["Owns the mistake", "What changed", "Learning applied later"]),
        ("Do you have any questions for us?", "Curiosity and preparation", ["Thoughtful, role-specific questions"]),
    ],
    "technical": [
        ("Tell me about yourself and the most relevant project for this {position} role.", "Relevant experience", ["Project scope", "Your contribution", "Technologies used"]),
        ("Walk me through how you would approach a typical problem in this {position} role.", "Problem-solving approach", ["Clarify requirements", "Step-by-step approach", "Trade-offs"]),
        ("Describe the hardest technical problem you've solved.", "Depth", ["Why it was hard", "How you solved it", "Result"]),
        ("How do you make sure your work is correct and of good quality?", "Quality practices", ["Testing / review", "Concrete examples"]),
        ("What would you do in your first 90 days in this role?", "Planning and fit", ["Learn the context", "Early contributions"]),
        ("Do you have any questions for us?", "Curiosity and preparation", ["Thoughtful, role-specific questions"]),
    ],
}


def _fallback_interview_plan(setup: dict, candidate_name: str | None = None) -> dict:
    kind = "technical" if setup.get("interview_type") == "technical" else "behavioural"
    bank = _QUESTION_BANK[kind]
    if setup.get("interview_type") == "mixed":
        bank = _QUESTION_BANK["behavioural"][:3] + _QUESTION_BANK["technical"][1:3] + _QUESTION_BANK["behavioural"][-1:]
    position = setup.get("position") or "this"
    questions = [{"question": q.format(position=position), "assesses": a, "look_for": lf} for q, a, lf in bank]
    company = f" at {setup['company']}" if setup.get("company") else ""
    return {
        "intro": f"Hi{' ' + candidate_name if candidate_name else ''}, I'm Alex, and I'll be interviewing you today "
                 f"for the {position} position{company}. {questions[0]['question']}",
        "questions": questions,
        "source": "rules",
    }


def _clean_question(text: str) -> str:
    """Drop a trailing category label the model sometimes appends: "… problem? (Role-Specific Problem Solving)"."""
    return re.sub(r"\s*\((?=[^)?]{2,60}\)\s*$)[^)]*\)\s*$", "", text).strip()


def _finish(plan: _Plan, name: str | None) -> dict:
    questions = [{**q.model_dump(), "question": _clean_question(q.question)} for q in plan.questions]
    return {"intro": _compose_intro(plan.greeting, questions[0]["question"], name), "questions": questions, "source": "llm"}


async def build_interview_plan(setup: dict, candidate_name: str | None = None) -> dict:
    try:
        payload = {**setup, **({"candidate_name": candidate_name} if candidate_name else {})}
        plan = await _llm_json(INTERVIEW_SYSTEM, payload, _Plan)
        if plan:
            return _finish(plan, candidate_name)
    except Exception as e:  # noqa: BLE001
        logger.error("Interview plan failed: %s", e)
    return _fallback_interview_plan(setup, candidate_name)


def _fallback_qa_plan(deck_title: str, insights: dict | None) -> dict:
    insights = insights or {}
    qs = [{"question": q, "slide_index": None, "assesses": "Answering audience questions",
           "look_for": ["Direct answer first", "Evidence from the talk"]} for q in insights.get("likely_questions", [])[:4]]
    for s in insights.get("slides", [])[1:3]:
        qs.append({"question": f"Could you explain a bit more about this point: {s['key_point']}?", "slide_index": s["slide_index"],
                   "assesses": "Depth on a key point", "look_for": ["Clear explanation", "An example"]})
    qs.append({"question": "What is the one thing you want us to remember from your talk?", "slide_index": None,
               "assesses": "Main message", "look_for": [insights.get("main_message") or "A one-sentence main message"]})
    qs = qs[:6] if len(qs) >= 3 else qs + [
        {"question": "What are the limitations of your approach?", "slide_index": None, "assesses": "Critical thinking", "look_for": ["Honest limits", "Mitigation"]},
        {"question": "What would you do next?", "slide_index": None, "assesses": "Next steps", "look_for": ["Concrete next step"]},
    ]
    return {"intro": f"Thank you for the presentation on “{deck_title}”. Let's open the floor for questions. {qs[0]['question']}",
            "questions": qs, "source": "rules"}


async def build_qa_plan(deck_title: str, insights: dict | None, requirement_prompt: str | None) -> dict:
    payload = {"deck_title": deck_title, "audience": requirement_prompt or "general audience",
               "insights": {k: (insights or {}).get(k) for k in ("summary", "main_message", "structure", "slides", "likely_questions")}}
    try:
        if insights:
            plan = await _llm_json(QA_SYSTEM, payload, _Plan)
            if plan:
                return _finish(plan, None)
    except Exception as e:  # noqa: BLE001
        logger.error("Q&A plan failed: %s", e)
    return _fallback_qa_plan(deck_title, insights)


# ── The AI partner during a planned session ────────────────────────────────
# The server, not the model, decides what comes next: a planned question is asked
# word-for-word, and a thin answer gets at most one follow-up. The LLM only writes the
# short reaction (and the follow-up), so even a small local model can't drift off-plan.

FOLLOWUP_WORDS = 25   # answers shorter than this get one follow-up question
CLOSING = {
    "Interview": "That's all the questions I have. Thank you for your time today; it was great talking with you. "
                 "You can end the session whenever you're ready to see your feedback.",
    "Presentation": "That's all the questions from the audience. Thank you, that was a good discussion. "
                    "You can end the session to see your feedback.",
}


def next_step(context: dict, last_answer: str | None) -> dict:
    """What the partner does next: {"action": "intro"|"ask"|"followup"|"close", "question": ...}.
    Mutates context["progress"]; the caller saves the context."""
    plan = context["plan"]
    qs = plan["questions"]
    prog = context.setdefault("progress", {"asked": 0, "followups": 0})
    if last_answer is None or prog["asked"] == 0:
        prog.update(asked=1, followups=0)
        return {"action": "intro", "question": qs[0]["question"]}
    if count_words(last_answer) < FOLLOWUP_WORDS and prog["followups"] == 0 and prog["asked"] <= len(qs):
        prog["followups"] = 1
        return {"action": "followup", "question": qs[prog["asked"] - 1]["question"]}
    if prog["asked"] >= len(qs):
        prog["asked"] = len(qs) + 1
        return {"action": "close", "question": None}
    q = qs[prog["asked"]]["question"]
    prog.update(asked=prog["asked"] + 1, followups=0)
    return {"action": "ask", "question": q}


def _role(session_type: str, context: dict) -> str:
    if session_type == "Interview":
        setup = context.get("setup", {})
        return (f"You are Alex, a friendly but professional interviewer for a {setup.get('level', '')} "
                f"{setup.get('position', '')} role{' at ' + setup['company'] if setup.get('company') else ''}.")
    return f"You are the moderator of the Q&A after a talk titled \"{context.get('deck_title', '')}\"."


async def planned_reply(session_type: str, context: dict, messages: list[dict]) -> str:
    """The partner's next line in an Interview / Presentation Q&A that follows a plan."""
    last_answer = next((m["content"] for m in reversed(messages) if m["role"] == "user"), None)
    step = next_step(context, last_answer)
    if step["action"] == "intro":
        return context["plan"]["intro"]
    client = get_llm_client()
    role = _role(session_type, context)
    last_q = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
    if step["action"] == "followup":
        instruction = ("Their answer was short. Ask ONE brief, specific follow-up question that helps them expand "
                       "(ask for an example, a result, or their own role). One sentence, no feedback, no scores.")
        fallback = "Could you give me a specific example of that, and what the result was?"
    else:
        instruction = ("Write ONE short, natural sentence reacting to their answer (mention something specific "
                       "they said). No question, no scores, no advice.")
        fallback = "Thank you, that's helpful."
    text = fallback
    if client is not None:
        try:
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "system", "content": f"{role} {instruction} Plain spoken sentence only, no markdown."},
                          {"role": "user", "content": f"You asked: {last_q}\nThey answered: {last_answer}"}],
                max_tokens=70, temperature=0.6,
            )
            text = (resp.choices[0].message.content or "").strip().strip('"') or fallback
        except Exception as e:  # noqa: BLE001
            logger.warning("Partner reaction failed, using fallback: %s", e)
    if step["action"] == "followup":
        return text
    if step["action"] == "close":
        return f"{text} {CLOSING.get(session_type, CLOSING['Interview'])}"
    return f"{text} {step['question']}"


# ── Content feedback after the session ──────────────────────────────────────

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
    went_well: str = Field(min_length=3, max_length=300)
    improve: str = Field(min_length=3, max_length=300)
    stronger_answer: str = Field(min_length=10, max_length=600)


class _AnswersReport(BaseModel):
    summary: str = Field(min_length=10, max_length=600)
    answers: list[_AnswerFeedback] = Field(max_length=MAX_PLAN_QUESTIONS + 4)


class _Correction(BaseModel):
    said: str = Field(min_length=1, max_length=300)
    better: str = Field(min_length=1, max_length=300)
    why: str = Field(min_length=3, max_length=200)


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
Be encouraging and concrete. Then a 2-sentence overall summary.
Return JSON only: {{"summary": "...", "answers": [{{"question", "relevance", "structure", "specificity", "went_well", "improve", "stronger_answer"}}]}}"""

CONVERSATION_SYSTEM = """You are a friendly English communication coach for a Malaysian learner. From the learner's turns in
a casual conversation, pick up to 5 real grammar or word-choice issues worth fixing (quote what they said, give the natural
version, explain briefly). Malaysian English expressions and particles like "lah" are fine — only correct things that would
confuse a listener or sound wrong in a formal setting. Add up to 3 tips about keeping a conversation going (asking questions
back, giving detail). Then a 2-sentence summary starting with something they did well.
Return JSON only: {"summary": "...", "corrections": [{"said", "better", "why"}], "tips": ["..."]}"""

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


async def content_feedback(session_type: str, context: dict | None, turns: list[dict] | None) -> dict | None:
    """Judge what was said (not how): per-answer for Interview / Presentation Q&A, corrections for Conversation."""
    pairs = pair_turns(turns or [])
    if not pairs:
        return None
    try:
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

            report = await _llm_json(system, payload, _AnswersReport, temperature=0.3, check=check)
            if report:
                for i, a in enumerate(report.answers):  # still inventing after the re-prompt: don't show a made-up answer
                    if invented_terms(a.stronger_answer, facts_for(i)):
                        a.stronger_answer = ("Lead with your main point, then the situation, what you did and the result, "
                                             "using your own details.")
                return {"kind": "answers", **report.model_dump(), "source": "llm"}
            answers = [_rule_answer(p, (plan_q.get(p["question"]) or {}).get("look_for")) for p in pairs]
            avg = sum(a["structure"] for a in answers) / len(answers)
            return {"kind": "answers", "source": "rules", "answers": answers,
                    "summary": f"You answered {len(answers)} question(s). "
                               + ("Your answers had clear structure — now add more specifics." if avg >= 4
                                  else "Use situation → action → result to give your answers more structure.")}
        # Conversation
        report = await _llm_json(CONVERSATION_SYSTEM, {"learner_turns": [p["answer"] for p in pairs],
                                                      "partner_turns": [p["question"] for p in pairs]}, _ConversationReport, 0.3)
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
    except Exception as e:  # noqa: BLE001
        logger.error("Content feedback failed: %s", e)
        return None
