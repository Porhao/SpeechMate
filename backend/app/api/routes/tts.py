from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.config.settings import settings

router = APIRouter(prefix="/tts", tags=["tts"])

# OpenAI voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer
# "nova" = warm, professional coaching voice
# "shimmer" = expressive, conversational
DEFAULT_VOICE = "nova"


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None


@router.post("/speak")
async def speak(body: TTSRequest):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    voice = body.voice or DEFAULT_VOICE
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        # Use streaming for lower latency
        async def stream():
            async with client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice=voice,
                input=text[:4096],
                response_format="mp3",
            ) as resp:
                async for chunk in resp.iter_bytes(chunk_size=4096):
                    yield chunk

        return StreamingResponse(
            stream(),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/voices")
def list_voices():
    return {
        "voices": [
            {"id": "nova",    "label": "Nova",    "desc": "Warm, professional — default coaching voice"},
            {"id": "shimmer", "label": "Shimmer", "desc": "Expressive, conversational"},
            {"id": "alloy",   "label": "Alloy",   "desc": "Neutral, balanced"},
            {"id": "echo",    "label": "Echo",    "desc": "Deep, calm"},
            {"id": "fable",   "label": "Fable",   "desc": "Authoritative, British"},
            {"id": "onyx",    "label": "Onyx",    "desc": "Deep male voice"},
            {"id": "coral",   "label": "Coral",   "desc": "Bright, energetic"},
            {"id": "sage",    "label": "Sage",    "desc": "Thoughtful, measured"},
        ]
    }
