"""FastAPI app entrypoint."""

from fastapi import FastAPI

from app.api.routes import heartbeat, ingest
from app.core.config import get_settings


def create_app() -> FastAPI:
    # Fail fast during app startup when boundary settings are invalid.
    get_settings()

    app = FastAPI(title="The Holding Cell Backend")
    app.include_router(ingest.router, prefix="/api", tags=["ingest"])
    app.include_router(heartbeat.router, prefix="/api", tags=["heartbeat"])
    return app


app = create_app()
