"""WebSocket origin policy checks shared with realtime server wiring."""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import Settings


def _normalize_origin(origin: str) -> str:
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.netloc:
        return origin.strip().rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def is_socket_origin_allowed(origin: str | None, settings: Settings) -> bool:
    if origin is None:
        return False
    normalized_origin = _normalize_origin(origin)
    allowed = {_normalize_origin(candidate) for candidate in settings.approved_browser_origins}
    return normalized_origin in allowed
