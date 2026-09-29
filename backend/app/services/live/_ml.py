"""Detects which optional local ML packages (requirements-ml.txt) are installed."""

import importlib.util
import threading
from collections.abc import Callable
from functools import cache, wraps
from typing import TypeVar

from app.config import settings


@cache
def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def available(*modules: str) -> bool:
    """True when local ML is enabled and every named package can be imported."""
    return settings.use_local_ml and all(_installed(m) for m in modules)


T = TypeVar("T")


def load_once(loader: Callable[[], T]) -> Callable[[], T]:
    """Cache a model loader, loading at most once even when several requests need it at
    the same moment (a bare lru_cache would load one copy per concurrent caller, which
    on a small machine means running out of memory). `.cache_clear()` frees it."""
    lock = threading.Lock()
    cached = cache(loader)

    @wraps(loader)
    def get() -> T:
        with lock:
            return cached()

    def cache_clear() -> None:
        with lock:
            cached.cache_clear()

    get.cache_clear = cache_clear  # type: ignore[attr-defined]
    return get
