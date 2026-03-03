"""Ingest endpoint routes."""

from fastapi import APIRouter, Depends

from app.schemas.ingest import IngestPayload
from app.security.forwarder_auth import require_trusted_forwarder

router = APIRouter()


@router.post("/ingest", status_code=202, dependencies=[Depends(require_trusted_forwarder)])
async def ingest_payload(payload: IngestPayload) -> dict[str, str]:
    return {"status": "accepted", "delivery_id": str(payload.delivery_id)}
