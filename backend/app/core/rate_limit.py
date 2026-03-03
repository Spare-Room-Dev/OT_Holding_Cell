"""Endpoint-level fixed-window rate limiting with retry contract metadata."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from threading import Lock

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.security.forwarder_auth import resolve_client_ip

RATE_LIMIT_EXCEEDED_MESSAGE = "Too many requests for this endpoint. Retry after the specified delay."


@dataclass(frozen=True)
class RateLimitResult:
    """Decision payload for a single rate-limit check."""

    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    reset_epoch: int


class RateLimitExceeded(Exception):
    """Raised when a request exceeds endpoint rate limits."""

    def __init__(self, result: RateLimitResult) -> None:
        self.result = result
        self.decision = result
        self.body = {
            "error": "rate_limit_exceeded",
            "message": RATE_LIMIT_EXCEEDED_MESSAGE,
            "retry_after_seconds": result.retry_after_seconds,
        }
        self.headers = {
            "Retry-After": str(result.retry_after_seconds),
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_epoch),
        }
        super().__init__(self.body["message"])


class FixedWindowLimiter:
    """Simple in-memory fixed-window limiter keyed by client identity."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def check(self, key: str) -> RateLimitResult:
        now = time.time()
        with self._lock:
            window_start, request_count = self._buckets.get(key, (now, 0))
            window_end = window_start + self.window_seconds

            if now >= window_end:
                window_start = now
                window_end = window_start + self.window_seconds
                request_count = 0

            if request_count >= self.max_requests:
                retry_after = max(1, int(math.ceil(window_end - now)))
                return RateLimitResult(
                    allowed=False,
                    limit=self.max_requests,
                    remaining=0,
                    retry_after_seconds=retry_after,
                    reset_epoch=int(math.ceil(window_end)),
                )

            request_count += 1
            self._buckets[key] = (window_start, request_count)
            remaining = max(self.max_requests - request_count, 0)
            return RateLimitResult(
                allowed=True,
                limit=self.max_requests,
                remaining=remaining,
                retry_after_seconds=0,
                reset_epoch=int(math.ceil(window_end)),
            )


_limiter_cache: dict[str, tuple[tuple[int, int], FixedWindowLimiter]] = {}
_cache_lock = Lock()


def reset_rate_limiters() -> None:
    """Clear all cached limiter state (used for app/test lifecycle isolation)."""

    with _cache_lock:
        _limiter_cache.clear()


def _get_limiter(name: str, max_requests: int, window_seconds: int) -> FixedWindowLimiter:
    config_tuple = (max_requests, window_seconds)
    with _cache_lock:
        cached = _limiter_cache.get(name)
        if cached is not None and cached[0] == config_tuple:
            return cached[1]

        limiter = FixedWindowLimiter(max_requests=max_requests, window_seconds=window_seconds)
        _limiter_cache[name] = (config_tuple, limiter)
        return limiter


def _request_key(request: Request) -> str:
    client_ip = resolve_client_ip(request)
    return client_ip or "unknown-client"


def require_ingest_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    limiter = _get_limiter(
        name="ingest",
        max_requests=settings.ingest_rate_limit_max_requests,
        window_seconds=settings.ingest_rate_limit_window_seconds,
    )
    result = limiter.check(_request_key(request))
    if not result.allowed:
        raise RateLimitExceeded(result)


def require_heartbeat_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    limiter = _get_limiter(
        name="heartbeat",
        max_requests=settings.heartbeat_rate_limit_max_requests,
        window_seconds=settings.heartbeat_rate_limit_window_seconds,
    )
    result = limiter.check(_request_key(request))
    if not result.allowed:
        raise RateLimitExceeded(result)


# Backward-compatible aliases for callers using older function names.
enforce_ingest_rate_limit = require_ingest_rate_limit
enforce_heartbeat_rate_limit = require_heartbeat_rate_limit
