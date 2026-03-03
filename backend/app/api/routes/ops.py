"""Operational visibility routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.enrichment_health_service import get_enrichment_queue_health

router = APIRouter()


class EnrichmentQueueHealthResponse(BaseModel):
    """Operator-facing queue pressure summary."""

    model_config = ConfigDict(extra="forbid")

    queued_count: int
    pending_count: int
    failed_count: int
    oldest_pending_age_seconds: Optional[int]


@router.get("/ops/enrichment-queue", response_model=EnrichmentQueueHealthResponse)
def get_enrichment_queue(
    session: Session = Depends(get_db_session),
) -> EnrichmentQueueHealthResponse:
    health = get_enrichment_queue_health(session=session)
    return EnrichmentQueueHealthResponse(
        queued_count=health.queued_count,
        pending_count=health.pending_count,
        failed_count=health.failed_count,
        oldest_pending_age_seconds=health.oldest_pending_age_seconds,
    )
