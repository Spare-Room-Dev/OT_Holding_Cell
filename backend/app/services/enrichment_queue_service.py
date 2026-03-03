"""Queue primitives for deferred enrichment processing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner
from app.services.enrichment_service import (
    ExistingEnrichmentState,
    enrich_ip_intel,
    merge_enrichment_result,
)

ACTIVE_ENRICHMENT_JOB_STATUSES = ("queued", "in_progress")
QUEUED_STATUS = "queued"
IN_PROGRESS_STATUS = "in_progress"
COMPLETED_STATUS = "completed"
FAILED_STATUS = "failed"


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


def claim_enrichment_jobs(
    *,
    session: Session,
    batch_size: int,
    now: datetime | None = None,
) -> list[EnrichmentJob]:
    """Claim the oldest available queued jobs in FIFO order."""

    if batch_size < 1:
        return []

    claim_time = _coerce_utc(now or datetime.now(timezone.utc))
    claim_ids = session.execute(
        select(EnrichmentJob.id)
        .where(
            EnrichmentJob.status == QUEUED_STATUS,
            EnrichmentJob.available_at <= claim_time,
        )
        .order_by(
            EnrichmentJob.available_at.asc(),
            EnrichmentJob.created_at.asc(),
            EnrichmentJob.id.asc(),
        )
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).scalars().all()
    if not claim_ids:
        return []

    claimed_jobs = session.execute(
        select(EnrichmentJob)
        .where(EnrichmentJob.id.in_(claim_ids))
        .order_by(
            EnrichmentJob.available_at.asc(),
            EnrichmentJob.created_at.asc(),
            EnrichmentJob.id.asc(),
        )
    ).scalars().all()

    for job in claimed_jobs:
        job.status = IN_PROGRESS_STATUS
        job.claimed_at = claim_time

    session.commit()
    for job in claimed_jobs:
        session.refresh(job)
    return claimed_jobs


def mark_enrichment_job_succeeded(
    *,
    session: Session,
    job_id: int,
    completed_at: datetime | None = None,
) -> EnrichmentJob | None:
    """Transition an in-progress job to terminal success."""

    event_time = _coerce_utc(completed_at or datetime.now(timezone.utc))
    job = session.execute(
        select(EnrichmentJob).where(EnrichmentJob.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if job is None:
        return None

    job.status = COMPLETED_STATUS
    job.completed_at = event_time
    job.claimed_at = None
    session.commit()
    session.refresh(job)
    return job


def mark_enrichment_job_failed(
    *,
    session: Session,
    job_id: int,
    reason_metadata: Mapping[str, str] | None = None,
    completed_at: datetime | None = None,
    attempt_count: int | None = None,
) -> EnrichmentJob | None:
    """Transition a job to terminal failed state with reason metadata."""

    event_time = _coerce_utc(completed_at or datetime.now(timezone.utc))
    job = session.execute(
        select(EnrichmentJob).where(EnrichmentJob.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if job is None:
        return None

    metadata = dict(job.failure_reason_metadata)
    if reason_metadata:
        metadata.update(dict(reason_metadata))

    job.status = FAILED_STATUS
    job.claimed_at = None
    job.completed_at = event_time
    if attempt_count is not None:
        job.attempt_count = max(job.attempt_count, attempt_count)
    job.failure_reason_metadata = metadata

    session.commit()
    session.refresh(job)
    return job


def _calculate_retry_delay_seconds(*, attempt_number: int, quota_limited: bool) -> int:
    settings = get_settings()
    if quota_limited:
        return settings.enrichment_quota_backoff_seconds

    exponential_backoff = settings.enrichment_retry_min_backoff_seconds * (2 ** max(attempt_number - 1, 0))
    return min(exponential_backoff, settings.enrichment_retry_max_backoff_seconds)


def defer_enrichment_job(
    *,
    session: Session,
    job_id: int,
    reason_metadata: Mapping[str, str] | None = None,
    now: datetime | None = None,
    quota_limited: bool = False,
) -> EnrichmentJob | None:
    """Defer a failed in-progress job with bounded retry semantics."""

    settings = get_settings()
    event_time = _coerce_utc(now or datetime.now(timezone.utc))
    job = session.execute(
        select(EnrichmentJob).where(EnrichmentJob.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if job is None:
        return None

    attempt_limit = min(job.max_attempts, settings.enrichment_retry_max_attempts)
    next_attempt = job.attempt_count + 1

    metadata = dict(job.failure_reason_metadata)
    if reason_metadata:
        metadata.update(dict(reason_metadata))

    if next_attempt >= attempt_limit:
        return mark_enrichment_job_failed(
            session=session,
            job_id=job_id,
            reason_metadata=metadata,
            completed_at=event_time,
            attempt_count=next_attempt,
        )

    retry_delay_seconds = _calculate_retry_delay_seconds(
        attempt_number=next_attempt,
        quota_limited=quota_limited,
    )

    job.status = QUEUED_STATUS
    job.attempt_count = next_attempt
    job.claimed_at = None
    job.completed_at = None
    job.available_at = event_time + timedelta(seconds=retry_delay_seconds)
    job.failure_reason_metadata = metadata

    session.commit()
    session.refresh(job)
    return job


def _build_existing_enrichment_state(prisoner: Prisoner) -> ExistingEnrichmentState:
    return ExistingEnrichmentState(
        status=prisoner.enrichment_status,
        country_code=prisoner.enrichment_country_code,
        asn=prisoner.enrichment_asn,
        reputation_severity=prisoner.enrichment_reputation_severity,
        reputation_confidence=prisoner.enrichment_reputation_confidence,
        reason_metadata=prisoner.enrichment_reason_metadata or {},
        provider=prisoner.enrichment_provider,
        last_enriched_at=prisoner.last_enriched_at,
    )


def _apply_prisoner_enrichment_update(*, prisoner: Prisoner, status_payload) -> None:
    prisoner.enrichment_status = status_payload.status
    prisoner.enrichment_country_code = status_payload.country_code
    prisoner.enrichment_asn = status_payload.asn
    prisoner.enrichment_reputation_severity = status_payload.reputation_severity
    prisoner.enrichment_reputation_confidence = status_payload.reputation_confidence
    prisoner.enrichment_reason_metadata = dict(status_payload.reason_metadata)
    prisoner.enrichment_provider = status_payload.provider
    if status_payload.last_enriched_at is not None:
        prisoner.last_enriched_at = status_payload.last_enriched_at


def process_next_batch(
    *,
    session: Session,
    batch_size: int,
    now: datetime | None = None,
) -> dict[str, int]:
    """Claim FIFO jobs and execute provider enrichment with bounded retries."""

    event_time = _coerce_utc(now or datetime.now(timezone.utc))
    claimed_jobs = claim_enrichment_jobs(
        session=session,
        batch_size=batch_size,
        now=event_time,
    )
    if not claimed_jobs:
        return {
            "claimed_count": 0,
            "processed_count": 0,
            "completed_count": 0,
            "deferred_count": 0,
            "failed_count": 0,
        }

    processed_count = 0
    completed_count = 0
    deferred_count = 0
    failed_count = 0

    for job in claimed_jobs:
        prisoner = session.execute(
            select(Prisoner).where(Prisoner.id == job.prisoner_id).with_for_update()
        ).scalar_one_or_none()
        if prisoner is None:
            mark_enrichment_job_failed(
                session=session,
                job_id=job.id,
                reason_metadata={"prisoner": "missing"},
                completed_at=event_time,
                attempt_count=job.attempt_count + 1,
            )
            processed_count += 1
            failed_count += 1
            continue

        provider_attempt = enrich_ip_intel(
            source_ip=prisoner.source_ip,
            now=event_time,
        )
        merged_result = merge_enrichment_result(
            previous=_build_existing_enrichment_state(prisoner),
            attempt=provider_attempt,
        )
        _apply_prisoner_enrichment_update(
            prisoner=prisoner,
            status_payload=merged_result,
        )

        if merged_result.status == "complete":
            mark_enrichment_job_succeeded(
                session=session,
                job_id=job.id,
                completed_at=event_time,
            )
            completed_count += 1
            processed_count += 1
            continue

        deferred_or_failed = defer_enrichment_job(
            session=session,
            job_id=job.id,
            reason_metadata=merged_result.reason_metadata,
            now=event_time,
            quota_limited=provider_attempt.quota_limited,
        )
        if deferred_or_failed is None:
            processed_count += 1
            continue

        if deferred_or_failed.status == FAILED_STATUS:
            failed_count += 1
        else:
            deferred_count += 1
        processed_count += 1

    return {
        "claimed_count": len(claimed_jobs),
        "processed_count": processed_count,
        "completed_count": completed_count,
        "deferred_count": deferred_count,
        "failed_count": failed_count,
    }
