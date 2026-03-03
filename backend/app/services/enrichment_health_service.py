"""Queue health metrics for deferred enrichment operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enrichment_job import EnrichmentJob

QUEUED_STATUS = "queued"
IN_PROGRESS_STATUS = "in_progress"
FAILED_STATUS = "failed"
PENDING_STATUSES = (QUEUED_STATUS, IN_PROGRESS_STATUS)


@dataclass(frozen=True)
class EnrichmentQueueHealth:
    queued_count: int
    pending_count: int
    failed_count: int
    oldest_pending_age_seconds: int | None


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _count_jobs(*, session: Session, status: str) -> int:
    return int(
        session.execute(
            select(func.count(EnrichmentJob.id)).where(EnrichmentJob.status == status)
        ).scalar_one()
    )


def get_enrichment_queue_health(
    *,
    session: Session,
    now: datetime | None = None,
) -> EnrichmentQueueHealth:
    """Return queue pressure and age signals for operator visibility."""

    now_utc = _coerce_utc(now or datetime.now(timezone.utc))

    queued_count = _count_jobs(session=session, status=QUEUED_STATUS)
    failed_count = _count_jobs(session=session, status=FAILED_STATUS)
    pending_count = int(
        session.execute(
            select(func.count(EnrichmentJob.id)).where(
                EnrichmentJob.status.in_(PENDING_STATUSES)
            )
        ).scalar_one()
    )

    oldest_pending_created_at = session.execute(
        select(func.min(EnrichmentJob.created_at)).where(
            EnrichmentJob.status.in_(PENDING_STATUSES)
        )
    ).scalar_one()

    oldest_pending_age_seconds: int | None = None
    if oldest_pending_created_at is not None:
        oldest_pending_age_seconds = max(
            0,
            int((now_utc - _coerce_utc(oldest_pending_created_at)).total_seconds()),
        )

    return EnrichmentQueueHealth(
        queued_count=queued_count,
        pending_count=pending_count,
        failed_count=failed_count,
        oldest_pending_age_seconds=oldest_pending_age_seconds,
    )
