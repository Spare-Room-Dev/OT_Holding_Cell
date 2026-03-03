"""Ingest endpoint routes."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/ingest", status_code=202)
async def ingest_payload() -> dict[str, str]:
    return {"status": "accepted"}
