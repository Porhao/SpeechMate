"""Request limits: upload size caps and a small per-key rate limiter.

The rate limiter is in-memory and per process, which is right for this single-process API
(uvicorn, one worker). ponytail: in-memory windows, use Redis (e.g. slowapi + redis) if the
API ever runs several workers or hosts.
"""

import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile

MB = 1024 * 1024
_CHUNK = 1 * MB


def too_large(what: str, max_bytes: int) -> HTTPException:
    return HTTPException(status_code=413, detail=f"{what} is too large: the limit is {max_bytes // MB} MB")


async def read_limited(file: UploadFile, max_bytes: int, what: str) -> bytes:
    """Read a small upload into memory, stopping as soon as it passes `max_bytes`."""
    if file.size is not None and file.size > max_bytes:
        raise too_large(what, max_bytes)
    chunks, total = [], 0
    while chunk := await file.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise too_large(what, max_bytes)
        chunks.append(chunk)
    return b"".join(chunks)


async def save_limited(file: UploadFile, dest: Path, max_bytes: int, what: str) -> None:
    """Stream a large upload to `dest` without holding it in memory; a partial file is removed."""
    if file.size is not None and file.size > max_bytes:
        raise too_large(what, max_bytes)
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with open(dest, "wb") as out:
            while chunk := await file.read(_CHUNK):
                total += len(chunk)
                if total > max_bytes:
                    raise too_large(what, max_bytes)
                out.write(chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise


class RateLimiter:
    """Sliding window: at most `limit` hits per `window_sec` for each key."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_sec: float) -> None:
        now = time.monotonic()
        q = self._hits[key]
        while q and q[0] <= now - window_sec:
            q.popleft()
        if len(q) >= limit:
            retry = int(q[0] + window_sec - now) + 1
            raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {retry} s.",
                                headers={"Retry-After": str(retry)})
        q.append(now)

    def reset(self) -> None:
        self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, limit: int, window_sec: float = 60):
    """FastAPI dependency: `limit` calls per `window_sec` per client IP for this endpoint."""
    def dep(request: Request) -> None:
        limiter.hit(f"{name}:{client_ip(request)}", limit, window_sec)
    return dep
