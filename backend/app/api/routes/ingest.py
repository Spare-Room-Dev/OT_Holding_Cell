"""Ingest endpoint routes."""

from fastapi import APIRouter, Depends

from app.security.forwarder_auth import require_trusted_forwarder

router = APIRouter()


@router.post("/ingest", status_code=202, dependencies=[Depends(require_trusted_forwarder)])
async def ingest_payload() -> dict[str, str]:
    return {"status": "accepted"}
