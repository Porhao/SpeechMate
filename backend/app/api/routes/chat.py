from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.config.settings import settings

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPTS: dict[str, str] = {
    "Conversation": """\
You are SpeechMate, a warm and encouraging English communication coach.
You are having a SPOKEN conversation with a Malaysian student practising English.

Rules:
- Keep every reply SHORT — 2 to 3 sentences maximum.
- DIRECTLY answer or react to what the user just said, then ask ONE natural follow-up question.
- If you spot a grammar or pronunciation issue, mention it briefly and gently.
- Never give long monologues. Keep the energy conversational and upbeat.
- Do NOT repeat the user's words back at length.""",

    "Interview": """\
You are a professional interviewer conducting a mock job interview for a Malaysian student.

Rules:
- Keep replies to 2-3 sentences.
- Briefly acknowledge their answer (1 sentence of specific feedback).
- Then ask your NEXT interview question — use standard behavioural questions (STAR method, strengths, weaknesses, scenarios, situational).
- Be professional but encouraging.
- Progress through different question types as the conversation continues.""",

    "Presentation": """\
You are a public speaking coach helping a student practise a presentation.

Rules:
- Keep replies SHORT — 2 sentences of coaching, then 1 instruction for what to do next.
- Comment specifically on structure, clarity, signpost language, pace, or audience engagement.
- Guide them through: opening hook → context → main arguments → transitions → conclusion.
- Be constructive and specific.""",

    "Pronunciation": """\
You are a pronunciation coach for a Malaysian English learner.

Rules:
- 1 to 2 sentences only.
- Comment specifically on what was correct and what sound needs work.
- Give ONE concrete tip (tongue position, stress pattern, etc.)
- Be encouraging.""",
}


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: str = "Conversation"
    topic: str | None = None


@router.post("/message")
async def chat_message(body: ChatRequest):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    system = SYSTEM_PROMPTS.get(body.mode, SYSTEM_PROMPTS["Conversation"])
    if body.topic:
        system += f"\n\nThe current conversation topic is: {body.topic}"

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                *[{"role": m.role, "content": m.content} for m in body.messages[-12:]],
            ],
            max_tokens=180,
            temperature=0.82,
        )
        reply = (resp.choices[0].message.content or "Could you say that again?").strip()
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
