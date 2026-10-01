"""Application configuration loaded from environment variables."""

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
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # Background jobs: how many pipelines (ideal, coach or live analysis) may run at once
    max_concurrent_jobs: int = 2

    # Auth (JWT). Generate a real secret with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

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
    vlm_model: str = "gpt-4o-mini"
    llm_model: str = "gpt-4o-mini"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    transcription_model: str = "whisper-1"
    ai_timeout_sec: float = 120.0
    # Voice for the live-session AI partner and /api/tts/speak
    coach_tts_voice: str = "nova"

    # ElevenLabs (voice cloning)
    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"

    # Live-session analysis: local models (installed from requirements-ml.txt).
    # Each one is skipped, with a warning, when its packages aren't installed.
    use_local_ml: bool = True
    # A size (tiny/base/small/medium/large-v3), a faster-whisper repo id, or the folder of a
    # converted model, e.g. /models/ct2/malaysian-whisper-small-v3 (scripts/convert_whisper.sh)
    whisper_model_size: str = "small"
    # CPU threads for Whisper; 0 = faster-whisper's default (4). 8 was fastest on a 24-core
    # machine (docs/benchmarks/stt-benchmark-2026-09-30.md); more threads start to contend.
    whisper_cpu_threads: int = 0
    # Language token for transcription. Empty = the model's own default: auto-detect for
    # Mesolitica's Malaysian Whisper (forcing "ms" makes it translate English into Malay),
    # "en" for standard Whisper (whose auto-detect sometimes hears Malaysian English as
    # Malay and translates it). "auto" = always detect; or force a code like "ms" / "en".
    stt_language: str = ""

    # Natural-sounding local TTS server with an OpenAI-compatible API, e.g. Kokoro-FastAPI
    # (TTS_BASE_URL=http://kokoro:8880/v1). Voices the live AI partner, and is a narration
    # fallback. Unset = OpenAI TTS (if keyed) / browser speech.
    tts_base_url: str | None = None
    local_tts_model: str = "kokoro"
    local_tts_voice: str = "af_heart"

    # Local Malaysian TTS (mesolitica/Malaysian-TTS-0.6B-v1): the default narrator
    # for presentation videos. Voice ids: see app/services/malaysian_tts.VOICES.
    malaysian_tts_voice: str = "husein"
    # Also use it for the live AI partner's voice (/api/tts/speak)? "auto" = only
    # on a CUDA GPU, where it's fast enough for conversation; "true" / "false" to force.
    live_tts_local: str = "auto"

    # Ideal Presentation Agent tuning
    script_min_words: int = 60
    script_max_words: int = 100

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
