"""FastAPI app entrypoint."""

from fastapi import FastAPI

from app.api.routes import heartbeat, ingest
from app.core.config import get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.middleware.body_size import BodySizeLimitMiddleware
from app.middleware.error_handlers import register_error_handlers

MAX_REQUEST_BODY_BYTES = 256 * 1024


def create_app() -> FastAPI:
    # Fail fast during app startup when boundary settings are invalid.
    get_settings()

    app = FastAPI(title="The Holding Cell Backend")
    app.state.rate_limiter = InMemoryRateLimiter()
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=MAX_REQUEST_BODY_BYTES)
    register_error_handlers(app)
    app.include_router(ingest.router, prefix="/api", tags=["ingest"])
    app.include_router(heartbeat.router, prefix="/api", tags=["heartbeat"])
    return app


app = create_app()
