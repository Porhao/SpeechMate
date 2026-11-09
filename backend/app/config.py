"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings, populated from environment variables or .env file."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://speechmate:speechmate_password@localhost/speechmate_db",
        description="Async database connection string",
    )

    # Storage
    storage_base_path: str = Field(
        default="./storage",
        description="Base directory for uploaded and generated files",
    )

    # API
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # Background jobs: how many pipelines (deck preparation or live analysis) may run at once
    max_concurrent_jobs: int = 2

    # Auth (JWT). Generate a real secret with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # Send the refresh cookie over HTTPS only. Keep false for http://localhost; set true when deployed on HTTPS.
    cookie_secure: bool = False
    # "none" when the frontend and API are on different sites (myapp.vercel.app + api.example.com);
    # needs cookie_secure. Same site (app.example.com + api.example.com) keeps "lax".
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    # PDPA: refuse to start cloud processing (Groq speech-to-text, Gemini) until the user agreed to it
    require_cloud_consent: bool = True

    # External binaries
    ffmpeg_bin: str = "ffmpeg"
    libreoffice_bin: str = "libreoffice"
    espeak_bin: str = "espeak-ng"

    # OpenAI: the default provider for everything (LLM, vision, TTS, Whisper)
    openai_api_key: str = ""
    openai_base_url: str | None = None

    # Separate LLM endpoint for text + vision only (chat, feedback, slide scripts),
    # e.g. a local Ollama: LLM_BASE_URL=http://ollama:11434/v1. Speech (TTS,
    # Whisper) still uses OpenAI or the local models. Unset = use OpenAI.
    llm_base_url: str | None = None
    llm_api_key: str = ""
    llm_timeout_sec: float = 300.0  # local models on CPU can be slow
    llm_model: str = "gpt-4o-mini"
    # List price of LLM_MODEL per million tokens, for the per-session cost (details.usage.llm.usd).
    # Defaults: Gemini 3.5 Flash-Lite paid tier (ai.google.dev/gemini-api/docs/pricing, 2026-10-20)
    llm_usd_per_m_input: float = 0.30
    llm_usd_per_m_output: float = 2.50
    tts_model: str = "gpt-4o-mini-tts"
    transcription_model: str = "whisper-1"
    ai_timeout_sec: float = 120.0
    # Voice for the live-session AI partner and /api/tts/speak
    coach_tts_voice: str = "nova"

    # Live-session analysis: local models (installed from requirements-ml.txt).
    # Each one is skipped, with a warning, when its packages aren't installed.
    use_local_ml: bool = True
    # Language token for transcription. Empty or "auto" = auto-detect (keeps Manglish as spoken);
    # or force a code like "ms" / "en" (a forced token makes Whisper translate other languages).
    stt_language: str = ""

    # Natural-sounding local TTS server with an OpenAI-compatible API, e.g. Kokoro-FastAPI
    # (TTS_BASE_URL=http://kokoro:8880/v1), for the live AI partner's voice when the browser's
    # own Kokoro isn't ready. Unset = OpenAI TTS (if keyed) / browser speech.
    tts_base_url: str | None = None
    local_tts_model: str = "kokoro"
    local_tts_voice: str = "af_heart"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        # Old .env files may still set removed options (ELEVENLABS_*, MALAYSIAN_TTS_VOICE…)
        "extra": "ignore",
    }


settings = Settings()
