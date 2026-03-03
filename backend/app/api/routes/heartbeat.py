"""Forwarder heartbeat routes."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/heartbeat", status_code=200)
async def heartbeat() -> dict[str, str]:
    return {"status": "ok"}
