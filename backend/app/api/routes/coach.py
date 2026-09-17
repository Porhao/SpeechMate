from fastapi import APIRouter, Depends, HTTPException
from app.config.settings import settings
from app.models.user import User
from app.schemas.session import ChatRequest, ChatResponse
from app.middleware.auth import get_current_user
from app.ai.llm.coach import get_coach_response

router = APIRouter(prefix="/coach", tags=["AI Coach"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    try:
        answer = await get_coach_response(body.question, body.history, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ChatResponse(answer=answer)
