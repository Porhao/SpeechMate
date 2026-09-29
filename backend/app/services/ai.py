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


def get_openai_client() -> AsyncOpenAI | None:
    """Return a shared OpenAI client, or None when no API key is configured."""
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
