"""Health check endpoint."""

import shutil

from fastapi import APIRouter

from app.config import settings
from app.services.ai import llm_provider
from app.services.live._ml import available

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Liveness check plus which binaries/providers are available (and so which fallbacks apply)."""
    return {
        "status": "ok",
        "service": "speechmate-api",
        "binaries": {
            "ffmpeg": shutil.which(settings.ffmpeg_bin) is not None,
            "libreoffice": shutil.which(settings.libreoffice_bin) is not None,
            "pdftoppm": shutil.which("pdftoppm") is not None,
            "espeak_ng": shutil.which(settings.espeak_bin) is not None,
        },
        # Optional local models for live-session analysis (requirements-ml.txt)
        "local_ml": {
            "faster_whisper": available("faster_whisper"),
            "wav2vec2": available("transformers", "torch"),
            "librosa": available("librosa"),
            "mediapipe": available("cv2", "mediapipe"),
        },
        # Where chat / feedback / slide-script calls go (LLM_BASE_URL = e.g. local Ollama)
        "llm": {
            "provider": llm_provider(),
            "base_url": settings.llm_base_url if settings.llm_base_url else None,
            "model": settings.llm_model if llm_provider() else None,
            "vision_model": settings.vlm_model if llm_provider() else None,
        },
        "providers": {
            "openai": bool(settings.openai_api_key),
            "elevenlabs": bool(settings.elevenlabs_api_key),
        },
    }
