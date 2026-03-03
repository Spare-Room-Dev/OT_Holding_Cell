"""Sanitized API error handlers for validation failures."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.rate_limit import RATE_LIMIT_EXCEEDED_MESSAGE, RateLimitExceeded

logger = logging.getLogger(__name__)

VALIDATION_ERROR_BODY = {
    "error": "validation_error",
    "message": "Invalid request payload",
}


def register_error_handlers(app: FastAPI) -> None:
    """Install sanitized validation handlers for hostile request traffic."""

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            "Request validation failed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),
            },
        )
        return JSONResponse(status_code=422, content=VALIDATION_ERROR_BODY)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        decision = exc.decision
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": RATE_LIMIT_EXCEEDED_MESSAGE,
                "retry_after_seconds": decision.retry_after_seconds,
            },
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Limit": str(decision.limit),
                "X-RateLimit-Remaining": str(decision.remaining),
                "X-RateLimit-Reset": str(decision.reset_epoch),
            },
        )
