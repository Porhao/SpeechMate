"""Who the AI is talking to: one short brief from the learner's profile, added to every LLM
prompt that faces them (the partner, interview and Q&A plans, answer feedback), so questions,
vocabulary and feedback fit their level, field and the feedback style they asked for.
Empty when nothing is set, and the prompts behave as before."""

from app.models.user import User

# How hard to push, by self-rated speaking level
LEVEL_GUIDE = {
    "Beginner": "Keep questions short and concrete, one idea at a time, everyday words; be patient and encouraging.",
    "Intermediate": "Use natural, everyday-professional language and ask for reasons and examples.",
    "Advanced": "Ask probing, multi-part questions with follow-ups that test reasoning; use precise vocabulary.",
}
STUDY_GUIDE = {
    "Secondary": "a secondary-school student (SPM level): school and everyday topics, no jargon",
    "Pre-university": "a pre-university / foundation / diploma student",
    "Undergraduate": "an undergraduate student",
    "Postgraduate": "a postgraduate student: academic depth is welcome",
    "Working professional": "a working professional: workplace situations fit best",
}
STYLE_GUIDE = {
    "encouraging": "Lead with what went well; at most two gentle, specific improvements.",
    "balanced": "Balance strengths and improvements, specific and kind.",
    "direct": "Be direct and concise: say plainly what to fix first, with no padding.",
}


def learner_brief(user: User | None) -> str:
    """'About the learner: …' for a system prompt, or '' when the profile is empty."""
    if user is None:
        return ""
    parts = []
    if user.study_level in STUDY_GUIDE:
        who = STUDY_GUIDE[user.study_level]
        parts.append(f"They are {who}" + (f", in {user.field_of_study.strip()}." if user.field_of_study and user.field_of_study.strip() else "."))
    elif user.field_of_study and user.field_of_study.strip():
        parts.append(f"Their field is {user.field_of_study.strip()}.")
    if user.skill_level in LEVEL_GUIDE:
        parts.append(f"Self-rated speaking level: {user.skill_level}. {LEVEL_GUIDE[user.skill_level]}")
    if user.communication_goal:
        parts.append(f"Their goal: {user.communication_goal}.")
    if user.challenges:
        parts.append(f"They are working on: {', '.join(user.challenges[:6])}.")
    if user.feedback_style in STYLE_GUIDE:
        parts.append(f"Feedback style they asked for: {STYLE_GUIDE[user.feedback_style]}")
    return ("About the learner (adapt to this; never mention it): " + " ".join(parts)) if parts else ""


def with_brief(system: str, brief: str) -> str:
    """`system` with a learner brief appended (unchanged when there is none)."""
    return f"{system}\n\n{brief}" if brief else system
