"""Queue primitives for deferred enrichment processing."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner

ACTIVE_ENRICHMENT_JOB_STATUSES = ("queued", "in_progress")


def _coerce_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def pending_enrichment_reason_metadata() -> dict[str, str]:
    return {
        "country_code": "pending",
        "asn": "pending",
        "reputation": "pending",
    }


def enqueue_prisoner_enrichment(
    *,
    session: Session,
    prisoner_id: int,
    available_at: datetime | None = None,
) -> EnrichmentJob:
    """Create one active queued enrichment job per prisoner."""

    settings = get_settings()
    enqueue_time = _coerce_utc(available_at or datetime.now(timezone.utc))

    # Locking the canonical prisoner row keeps active-job checks deterministic under races.
    session.execute(
        select(Prisoner.id).where(Prisoner.id == prisoner_id).with_for_update()
    ).scalar_one()

    existing_active_job = session.execute(
        select(EnrichmentJob)
        .where(
            EnrichmentJob.prisoner_id == prisoner_id,
            EnrichmentJob.status.in_(ACTIVE_ENRICHMENT_JOB_STATUSES),
        )
        .order_by(EnrichmentJob.created_at.asc(), EnrichmentJob.id.asc())
        .with_for_update()
    ).scalar_one_or_none()
    if existing_active_job is not None:
        return existing_active_job

    job = EnrichmentJob(
        prisoner_id=prisoner_id,
        status="queued",
        attempt_count=0,
        max_attempts=settings.enrichment_retry_max_attempts,
        available_at=enqueue_time,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
