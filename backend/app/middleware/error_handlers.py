"""Sanitized API error handlers for validation failures."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
