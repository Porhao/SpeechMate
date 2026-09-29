"""Shared helpers for external AI calls: client construction and retries."""

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import TypeVar

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_openai_client: AsyncOpenAI | None = None


_llm_client: AsyncOpenAI | None = None


def llm_provider() -> str | None:
    """Where LLM/VLM calls go: "custom" (LLM_BASE_URL, e.g. Ollama), "openai", or None."""
    if settings.llm_base_url:
        return "custom"
    if settings.openai_api_key:
        return "openai"
    return None


def get_llm_client() -> AsyncOpenAI | None:
    """Client for text + vision calls (chat, feedback, slide scripts), or None if no LLM is configured.

    LLM_BASE_URL points these at any OpenAI-compatible server — Ollama, vLLM,
    LM Studio, Gemini's or DashScope's compatible endpoints — independently of
    speech, which stays on OpenAI / local models (see get_openai_client).
    """
    global _llm_client
    if not settings.llm_base_url:
        return get_openai_client()
    if _llm_client is None:
        _llm_client = AsyncOpenAI(
            api_key=settings.llm_api_key or "not-needed",  # Ollama ignores it, the SDK requires one
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_sec,
            max_retries=0,
        )
    return _llm_client


async def unload_local_model(model: str) -> None:
    """Ask an Ollama server to drop `model` from memory now instead of after its idle timeout.

    Used on small machines between pipeline stages (e.g. free the vision model
    before the TTS model loads). A no-op for OpenAI or non-Ollama servers.
    """
    base = settings.llm_base_url
    if not base or not base.rstrip("/").endswith("/v1"):
        return
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as http:
            await http.post(f"{base.rstrip('/')[:-3]}/api/generate", json={"model": model, "keep_alive": 0})
    except Exception as e:  # noqa: BLE001 — best effort
        logger.debug("Could not unload %s: %s", model, e)


def get_openai_client() -> AsyncOpenAI | None:
    """Shared OpenAI client (used directly for speech: TTS and Whisper), or None without an API key."""
    global _openai_client
    if not settings.openai_api_key:
        return None
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
            timeout=settings.ai_timeout_sec,
            max_retries=0,  # retries are handled by with_retries()
        )
    return _openai_client


async def with_retries(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 1.5,
    label: str = "call",
) -> T:
    """Run an async call with exponential backoff. Re-raises the last error."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as e:  # noqa: BLE001 — every provider error should be retried
            last_error = e
            logger.warning("%s failed (attempt %d/%d): %s", label, attempt, attempts, e)
            if attempt < attempts:
                await asyncio.sleep(base_delay * 2 ** (attempt - 1))
    assert last_error is not None
    raise last_error


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from an LLM reply, tolerating ```json fences."""
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data
