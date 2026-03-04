"""FastAPI app entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import heartbeat, ingest, ops, prisoners
from app.core.config import get_settings
from app.core.rate_limit import reset_rate_limiters
import app.db.session as db_session_module
from app.middleware.body_size import BodySizeLimitMiddleware
from app.middleware.error_handlers import register_error_handlers
from app.realtime.stats_broadcaster import RealtimeStatsBroadcaster
from app.realtime import socket_server

MAX_REQUEST_BODY_BYTES = 256 * 1024


@asynccontextmanager
async def _app_lifespan(app: FastAPI):
    stats_broadcaster = RealtimeStatsBroadcaster(
        session_factory=db_session_module.SessionFactory,
        event_bus=socket_server.realtime_event_bus,
    )
    app.state.stats_broadcaster = stats_broadcaster
    await stats_broadcaster.start()
    try:
        yield
    finally:
        await stats_broadcaster.stop()


def create_app() -> FastAPI:
    # Fail fast during app startup when boundary settings are invalid.
    settings = get_settings()
    reset_rate_limiters()

    app = FastAPI(title="The Holding Cell Backend", lifespan=_app_lifespan)
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
    app.include_router(socket_server.router, tags=["realtime"])
    return app


app = create_app()
