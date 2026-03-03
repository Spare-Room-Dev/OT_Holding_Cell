"""Forwarder heartbeat routes."""

from fastapi import APIRouter, Depends

from app.security.forwarder_auth import require_trusted_forwarder

router = APIRouter()


@router.post("/heartbeat", status_code=200, dependencies=[Depends(require_trusted_forwarder)])
async def heartbeat() -> dict[str, str]:
    return {"status": "ok"}
