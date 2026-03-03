"""ASGI middleware that rejects oversized request bodies before parsing."""

from __future__ import annotations

from typing import Optional

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLarge(Exception):
    """Raised when a streaming request body exceeds configured size limits."""


class BodySizeLimitMiddleware:
    """Apply a hard request-body cap to HTTP traffic."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = self._extract_content_length(scope)
        if content_length is not None and content_length > self.max_body_bytes:
            await self._send_rejection(scope, receive, send)
            return

        consumed = 0

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_body_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            await self._send_rejection(scope, receive, send)

    @staticmethod
    def _extract_content_length(scope: Scope) -> Optional[int]:
        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == b"content-length":
                try:
                    return int(header_value.decode("ascii"))
                except (ValueError, UnicodeDecodeError):
                    return None
        return None

    @staticmethod
    async def _send_rejection(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "error": "payload_too_large",
                "message": "Request body exceeds allowed size",
            },
        )
        await response(scope, receive, send)
