"""The AI practice partner's next spoken line in a live session.

- Free conversation: the persona prompt for the mode, with the learner brief and topic.
- Interview / Presentation Q&A with a plan: the server, not the model, decides what comes next
  (next_step), and the LLM only writes the short reaction, follow-up or answer, so even a small
  model can't drift off-plan. Works without an LLM (fixed lines)."""

import logging
import re
from pathlib import Path

from app.services.ai import llm_text
from app.services.learner import with_brief
from app.services.text import count_words

logger = logging.getLogger(__name__)

HISTORY_TURNS = 12  # messages of history the free partner sees (the frontend sends the same window)

# Replies are spoken aloud, so they must read like natural speech
SPOKEN_STYLE = """

Speak like a real person in a relaxed voice conversation:
- Use contractions and everyday phrasing ("that's great", "let's try", "you know what").
- Vary your sentence length; it's fine to start with a short reaction like "Oh nice!" or "Hmm, good point."
- Plain sentences only: no lists, bullet points, headings, emoji, asterisks or markdown — everything you write is read aloud by a text-to-speech voice.
- Never say you are an AI unless asked."""

# One persona per practice mode (edit the wording in the text files)
_PROMPTS = Path(__file__).parent.parent / "prompts"
PERSONAS: dict[str, str] = {
    mode: (_PROMPTS / name).read_text(encoding="utf-8").strip()
    for mode, name in {
        "Conversation": "conversation_partner.txt",
        "Interview": "interview_partner.txt",
        "Presentation": "qa_moderator.txt",
    }.items()
}
OPENER = "(The learner has just joined. Greet them warmly and open the conversation.)"
NO_QUESTION_NUDGE = ("\n\nYour last two replies both ended with a question. This time do NOT ask anything: react, then "
                     "share your own opinion, a short story or a playful comment they can respond to.")


async def free_reply(mode: str, messages: list[dict], topic: str | None, learner: str) -> str | None:
    """The partner's next line in an unplanned session, or None without a working LLM."""
    system = with_brief(PERSONAS.get(mode, PERSONAS["Conversation"]) + SPOKEN_STYLE, learner)
    if topic:
        system += f"\n\nThe current conversation topic is: {topic}"
    # Models drift back into interviewing: after two questions in a row, the next turn is a comment
    recent = [m["content"].rstrip() for m in messages if m["role"] == "assistant"][-2:]
    if mode == "Conversation" and len(recent) == 2 and all(r.endswith("?") for r in recent):
        system += NO_QUESTION_NUDGE
    history = messages[-HISTORY_TURNS:] or [{"role": "user", "content": OPENER}]
    return await llm_text(system, history, max_tokens=180, temperature=0.82)


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


_QUESTION_START = re.compile(
    r"^(what|how|why|when|where|who|which|could|can|do|does|did|is|are|was|will|would|should|may)\b", re.I)


def asks_question(text: str | None) -> bool:
    """Did the learner end their turn by asking the partner something? ("What does the team work on?")
    Whisper punctuates, so a final "?" is the main signal; a question-word start covers a missed "?"."""
    # ponytail: heuristic on the last sentence; ask the LLM to classify if rhetorical questions misfire
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if x]
    if not sentences:
        return False
    last = sentences[-1]
    return last.endswith("?") or (bool(_QUESTION_START.match(last)) and not last.endswith("."))


def invites_questions(question: str) -> bool:
    """The planned "Do you have any questions for us?" turn."""
    return bool(re.search(r"\bany questions\b|\banything you'?d like to ask\b", question, re.I))


def next_step(context: dict, last_answer: str | None) -> dict:
    """What the partner does next: {"action": "intro"|"ask"|"followup"|"answer"|"close", "question": ...}.
    "answer": the learner asked something; reply to it without moving on, then `question` (the one
    still open) is put back to them. Mutates context["progress"]; the caller saves the context."""
    plan = context["plan"]
    qs = plan["questions"]
    prog = context.setdefault("progress", {"asked": 0, "followups": 0})
    if last_answer is None or prog["asked"] == 0:
        prog.update(asked=1, followups=0)
        return {"action": "intro", "question": qs[0]["question"]}
    current = qs[min(prog["asked"], len(qs)) - 1]["question"]
    open_floor = prog["asked"] > len(qs) or invites_questions(current)
    if asks_question(last_answer):
        # Their question to us ("Do you have any questions for us?"): answer, then invite another one
        return {"action": "answer", "question": None if open_floor else current}
    if (count_words(last_answer) < FOLLOWUP_WORDS and prog["followups"] == 0 and prog["asked"] <= len(qs)
            and not open_floor):  # "No, that's all" needs no "give me an example"
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
    role = _role(session_type, context)
    last_q = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
    if step["action"] == "answer":
        who = "the interviewer" if session_type == "Interview" else "the moderator, speaking for the audience"
        instruction = (f"They asked you a question. Answer it directly and helpfully as {who}, in 2-3 sentences, like a "
                       "real person would. Speak generally about the role, team, culture, growth and next steps; never invent "
                       "specific facts such as salaries, names, numbers or dates. If it asks you to repeat or explain your "
                       "question, do that instead. Don't ask a question back.")
        fallback = "That's a good question. It really depends on the team, and it's something to explore further in the next round."
    elif step["action"] == "followup":
        instruction = ("Their answer was short. Ask ONE brief, specific follow-up question that helps them expand "
                       "(ask for an example, a result, or their own role). One sentence, no feedback, no scores.")
        fallback = "Could you give me a specific example of that, and what the result was?"
    else:
        instruction = ("Write ONE short, natural sentence reacting to their answer (mention something specific "
                       "they said). No question, no scores, no advice.")
        fallback = "Thank you, that's helpful."
    text = await llm_text(f"{role} {instruction} Plain spoken sentence only, no markdown.",
                          [{"role": "user", "content": f"You asked: {last_q}\nThey answered: {last_answer}"}],
                          max_tokens=160 if step["action"] == "answer" else 70, temperature=0.6) or fallback
    if step["action"] == "followup":
        return text
    if step["action"] == "answer":
        # An open planned question goes back to them; at the end, invite another question
        return f"{text} {'So, back to my question: ' + step['question'] if step['question'] else 'Is there anything else you would like to ask?'}"
    if step["action"] == "close":
        return f"{text} {CLOSING.get(session_type, CLOSING['Interview'])}"
    return f"{text} {step['question']}"


async def next_line(mode: str, context: dict, messages: list[dict], topic: str | None, learner: str) -> str | None:
    """The partner's next line: following the session's plan when it has one (mutates context["progress"]),
    else free conversation. None only when a free conversation has no working LLM."""
    if context.get("plan"):
        return await planned_reply(mode, context, messages)
    return await free_reply(mode, messages, topic or context.get("topic"), learner)
