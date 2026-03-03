"""Retention lifecycle service with rollup preservation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ingest_delivery import IngestDelivery
from app.models.lifetime_rollup import LifetimeRollup
from app.models.prisoner import Prisoner
from app.models.retention_run import RetentionRun

UNKNOWN_COUNTRY = "UNKNOWN"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _normalize_country_code(country_code: Optional[str]) -> str:
    if not country_code:
        return UNKNOWN_COUNTRY
    return country_code.upper()


def _upsert_rollup(
    *,
    session: Session,
    rollup_key: str,
    country_code: Optional[str],
    attempts: int,
    as_of: datetime,
) -> None:
    if attempts <= 0:
        return

    rollup = session.execute(
        select(LifetimeRollup).where(LifetimeRollup.rollup_key == rollup_key)
    ).scalar_one_or_none()
    if rollup is None:
        session.add(
            LifetimeRollup(
                rollup_key=rollup_key,
                country_code=country_code,
                attempt_count=attempts,
                created_at=as_of,
                updated_at=as_of,
            )
        )
        return

    rollup.attempt_count += attempts
    rollup.updated_at = as_of


def run_retention_cycle(*, session: Session, now: Optional[datetime] = None) -> dict[str, object]:
    """Purge expired detail records while preserving lifetime headline rollups."""

    settings = get_settings()
    started_at = _coerce_utc(now or _utc_now())
    prisoner_cutoff = started_at - timedelta(days=settings.retention_prisoner_days)
    delivery_cutoff = started_at - timedelta(days=settings.retention_delivery_days)

    deleted_prisoner_count = 0
    deleted_delivery_count = 0
    try:
        expired_prisoners = session.execute(
            select(Prisoner).where(Prisoner.last_seen_at < prisoner_cutoff)
        ).scalars().all()

        deleted_prisoner_count = len(expired_prisoners)
        total_attempts = 0
        attempts_by_country: dict[str, int] = {}
        expired_ids: list[int] = []

        for prisoner in expired_prisoners:
            expired_ids.append(prisoner.id)
            attempts = max(prisoner.attempt_count, 0)
            total_attempts += attempts

            country_code = _normalize_country_code(prisoner.country_code)
            attempts_by_country[country_code] = attempts_by_country.get(country_code, 0) + attempts

        _upsert_rollup(
            session=session,
            rollup_key="overall",
            country_code=None,
            attempts=total_attempts,
            as_of=started_at,
        )
        for country_code, attempts in attempts_by_country.items():
            _upsert_rollup(
                session=session,
                rollup_key=f"country:{country_code}",
                country_code=country_code,
                attempts=attempts,
                as_of=started_at,
            )

        if expired_ids:
            session.execute(delete(Prisoner).where(Prisoner.id.in_(expired_ids)))

        delivery_result = session.execute(
            delete(IngestDelivery).where(IngestDelivery.created_at < delivery_cutoff)
        )
        deleted_delivery_count = delivery_result.rowcount or 0

        finished_at = _utc_now()
        retention_run = RetentionRun(
            started_at=started_at,
            finished_at=finished_at,
            prisoner_cutoff_at=prisoner_cutoff,
            delivery_cutoff_at=delivery_cutoff,
            deleted_prisoner_count=deleted_prisoner_count,
            deleted_delivery_count=deleted_delivery_count,
            status="succeeded",
            error_message=None,
        )
        session.add(retention_run)
        session.commit()

        return {
            "status": "succeeded",
            "run_id": retention_run.id,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "deleted_prisoner_count": deleted_prisoner_count,
            "deleted_delivery_count": deleted_delivery_count,
            "prisoner_cutoff_at": prisoner_cutoff.isoformat(),
            "delivery_cutoff_at": delivery_cutoff.isoformat(),
        }
    except Exception as exc:
        session.rollback()

        finished_at = _utc_now()
        failed_run = RetentionRun(
            started_at=started_at,
            finished_at=finished_at,
            prisoner_cutoff_at=prisoner_cutoff,
            delivery_cutoff_at=delivery_cutoff,
            deleted_prisoner_count=0,
            deleted_delivery_count=0,
            status="failed",
            error_message=str(exc)[:1024],
        )
        session.add(failed_run)
        session.commit()
        raise
