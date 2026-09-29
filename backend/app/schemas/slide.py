"""Pydantic schemas for slide data."""

from pydantic import BaseModel, ConfigDict


class SlideScript(BaseModel):
    """A single slide's script data, with its position in the ideal video."""
    model_config = ConfigDict(from_attributes=True)

    slide_index: int
    script_text: str | None = None
    word_count: int | None = None
    script_source: str | None = None  # vlm | fallback
    audio_source: str | None = None  # elevenlabs_clone | openai_tts | espeak | silence
    # Where this slide starts/lasts in ideal_video.mp4 (for syncing the script panel)
    start_sec: float | None = None
    duration_sec: float | None = None
    status: str


class SlideScriptsResponse(BaseModel):
    """All scripts for a session."""
    slides: list[SlideScript]
