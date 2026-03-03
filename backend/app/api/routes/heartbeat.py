"""Forwarder heartbeat routes."""

from fastapi import APIRouter, Depends

from app.core.rate_limit import require_heartbeat_rate_limit
from app.schemas.heartbeat import HeartbeatPayload
from app.security.forwarder_auth import require_trusted_forwarder

router = APIRouter()


@router.post(
    "/heartbeat",
    status_code=200,
    dependencies=[Depends(require_trusted_forwarder), Depends(require_heartbeat_rate_limit)],
)
async def heartbeat(payload: HeartbeatPayload) -> dict[str, str]:
    return {"status": "ok", "protocol": payload.protocol}
