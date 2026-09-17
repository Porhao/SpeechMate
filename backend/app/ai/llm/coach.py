from openai import AsyncOpenAI
from app.config.settings import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """You are SpeechMate AI Coach, an expert communication trainer specializing in:
- Speech fluency and stuttering improvement
- Pronunciation coaching (English and Bahasa Melayu)
- Public speaking and presentation skills
- Communication confidence building
- Eye contact and non-verbal communication

Provide concise, actionable, encouraging feedback. Never shame the user.
Always frame improvements positively and specifically."""


async def get_coach_response(question: str, history: list[dict], user_id: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-10:])  # Keep last 10 turns for context
    messages.append({"role": "user", "content": question})

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message.content or ""
