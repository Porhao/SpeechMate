"""Question plans for the curated practice: an interview plan from the candidate's setup (and resume),
and the audience's Q&A plan from a deck's insights. Each question says what it assesses and what a
strong answer contains. Without an LLM, a rule-based plan from a question bank / the deck."""

import logging
import re

from pydantic import BaseModel, Field

from app.schemas.live import PlanQuestion
from app.services.ai import llm_json
from app.services.learner import with_brief

logger = logging.getLogger(__name__)

MAX_PLAN_QUESTIONS = 8


class _LLMQuestion(PlanQuestion):
    """A plan question as the LLM must write it: stricter than what the API accepts back."""
    question: str = Field(min_length=8, max_length=400)
    assesses: str = Field(min_length=3, max_length=200)
    look_for: list[str] = Field(min_length=1, max_length=5)


class _Plan(BaseModel):
    greeting: str = Field(default="", max_length=600)  # the Q&A moderator's; the interviewer's is built in code
    questions: list[_LLMQuestion] = Field(min_length=3, max_length=MAX_PLAN_QUESTIONS)


def _compose_intro(greeting: str, first_question: str) -> str:
    """The spoken opening: the model's greeting (any [placeholder] or question in it dropped)
    followed by planned question 1 word-for-word, so the plan and the conversation never drift."""
    greeting = re.sub(r"\[[^\]]*\]", "", greeting).lstrip(".…,;: ")
    greeting = re.sub(r"([,.!])\1+", r"\1", re.sub(r"\s+([,.!])", r"\1", re.sub(r"\s{2,}", " ", greeting))).strip()
    sentences = re.split(r"(?<=[.!?])\s+", greeting)
    keep = [x for x in sentences if x and not x.endswith("?")
            and not re.search(r"\b(tell me|let's start|opener|first question)\b", x, re.I)]
    return " ".join(keep[:2] + [first_question]).strip()


INTERVIEW_SYSTEM = """You are an experienced hiring manager preparing a realistic mock interview.
From the candidate's setup (and resume, if given) write a plan of 6-8 questions in the order you'd ask them:
start with a warm opener ("tell me about yourself" tailored to the role), then questions that test what THIS
role needs at THIS level, referencing the candidate's real experience/resume where useful, and finish with
"Do you have any questions for us?". Match the interview type (behavioural → STAR situations; technical →
role-specific problem solving; mixed → both). For each question say what it assesses and 2-4 things a strong
answer contains. Each "question" is exactly what you'd say aloud: no labels, categories or numbering.
Return JSON only: {"questions": [{"question": "...", "assesses": "...", "look_for": ["..."]}]}"""

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


def _interview_greeting(setup: dict, candidate_name: str | None) -> str:
    """Built from the setup, not by the model: a small model mixes up the slots (it once
    greeted "Aisyah" for "the Data Analyst position at Aisyah" when no company was given)."""
    position = setup.get("position") or "this"
    company = f" at {setup['company']}" if setup.get("company") else ""
    return (f"Hi{' ' + candidate_name if candidate_name else ''}, I'm Alex, and I'll be interviewing you today "
            f"for the {position} position{company}.")


def _fallback_interview_plan(setup: dict, candidate_name: str | None = None) -> dict:
    kind = "technical" if setup.get("interview_type") == "technical" else "behavioural"
    bank = _QUESTION_BANK[kind]
    if setup.get("interview_type") == "mixed":
        bank = _QUESTION_BANK["behavioural"][:3] + _QUESTION_BANK["technical"][1:3] + _QUESTION_BANK["behavioural"][-1:]
    position = setup.get("position") or "this"
    questions = [{"question": q.format(position=position), "assesses": a, "look_for": lf} for q, a, lf in bank]
    return {
        "intro": f"{_interview_greeting(setup, candidate_name)} {questions[0]['question']}",
        "questions": questions,
        "source": "rules",
    }


def _clean_question(text: str) -> str:
    """Drop a trailing category label the model sometimes appends: "… problem? (Role-Specific Problem Solving)"."""
    return re.sub(r"\s*\((?=[^)?]{2,60}\)\s*$)[^)]*\)\s*$", "", text).strip()


def _questions(plan: _Plan) -> list[dict]:
    return [{**q.model_dump(), "question": _clean_question(q.question)} for q in plan.questions]


async def build_interview_plan(setup: dict, candidate_name: str | None = None, learner: str = "") -> dict:
    """`learner`: services/learner.py's brief, so the questions fit the candidate's level and field."""
    try:
        plan = await llm_json(with_brief(INTERVIEW_SYSTEM, learner), setup, _Plan)
        if plan:
            questions = _questions(plan)
            return {"intro": f"{_interview_greeting(setup, candidate_name)} {questions[0]['question']}",
                    "questions": questions, "source": "llm"}
    except Exception as e:  # noqa: BLE001
        logger.error("Interview plan failed: %s", e)
    return _fallback_interview_plan(setup, candidate_name)


def _fallback_qa_plan(deck_title: str, insights: dict) -> dict:
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


async def build_qa_plan(deck_title: str, insights: dict, requirement_prompt: str | None, learner: str = "") -> dict:
    payload = {"deck_title": deck_title, "audience": requirement_prompt or "general audience",
               "insights": {k: insights.get(k) for k in ("summary", "main_message", "structure", "slides", "likely_questions")}}
    try:
        plan = await llm_json(with_brief(QA_SYSTEM, learner), payload, _Plan)
        if plan:
            questions = _questions(plan)
            return {"intro": _compose_intro(plan.greeting, questions[0]["question"]), "questions": questions, "source": "llm"}
    except Exception as e:  # noqa: BLE001
        logger.error("Q&A plan failed: %s", e)
    return _fallback_qa_plan(deck_title, insights)
