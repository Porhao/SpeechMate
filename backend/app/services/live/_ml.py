"""Detects which optional local ML packages (requirements-ml.txt) are installed."""

import importlib.util
from functools import cache

from app.config import settings


@cache
def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def available(*modules: str) -> bool:
    """True when local ML is enabled and every named package can be imported."""
    return settings.use_local_ml and all(_installed(m) for m in modules)
