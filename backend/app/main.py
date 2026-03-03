"""FastAPI app entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import heartbeat, ingest, ops, prisoners
from app.core.config import get_settings
from app.core.rate_limit import reset_rate_limiters
from app.middleware.body_size import BodySizeLimitMiddleware
from app.middleware.error_handlers import register_error_handlers

MAX_REQUEST_BODY_BYTES = 256 * 1024


def create_app() -> FastAPI:
    # Fail fast during app startup when boundary settings are invalid.
    settings = get_settings()
    reset_rate_limiters()

    app = FastAPI(title="The Holding Cell Backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.approved_browser_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Forwarded-For"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=MAX_REQUEST_BODY_BYTES)
    register_error_handlers(app)
    app.include_router(ingest.router, prefix="/api", tags=["ingest"])
    app.include_router(heartbeat.router, prefix="/api", tags=["heartbeat"])
    app.include_router(prisoners.router, prefix="/api", tags=["prisoners"])
    app.include_router(ops.router, prefix="/api", tags=["ops"])
    return app


app = create_app()
