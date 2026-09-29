"""Health check endpoint."""

import shutil

from fastapi import APIRouter

from app.config import settings
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
        "providers": {
            "openai": bool(settings.openai_api_key),
            "elevenlabs": bool(settings.elevenlabs_api_key),
        },
    }
