"""Canonical realtime stats aggregation for snapshots and live broadcasts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.lifetime_rollup import LifetimeRollup
from app.models.prisoner import Prisoner

ACTIVE_WINDOW_HOURS = 24
LIFETIME_ROLLUP_KEY = "overall"


def _coerce_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_realtime_stats_snapshot(
    *,
    session: Session,
    now: datetime | None = None,
) -> dict[str, int]:
    """Return deterministic aggregate counters for realtime stats payloads."""

    anchor = _coerce_utc(now)
    active_cutoff = anchor - timedelta(hours=ACTIVE_WINDOW_HOURS)

    total_prisoners = int(
        session.execute(select(func.count(Prisoner.id))).scalar_one()
    )
    active_prisoners = int(
        session.execute(
            select(func.count(Prisoner.id)).where(Prisoner.last_seen_at >= active_cutoff)
        ).scalar_one()
    )

    current_attempts = int(
        session.execute(
            select(func.coalesce(func.sum(Prisoner.attempt_count), 0))
        ).scalar_one()
    )
    current_credentials = int(
        session.execute(
            select(func.coalesce(func.sum(Prisoner.credential_count), 0))
        ).scalar_one()
    )
    current_commands = int(
        session.execute(
            select(func.coalesce(func.sum(Prisoner.command_count), 0))
        ).scalar_one()
    )
    current_downloads = int(
        session.execute(
            select(func.coalesce(func.sum(Prisoner.download_count), 0))
        ).scalar_one()
    )

    lifetime_rollup_attempts = session.execute(
        select(LifetimeRollup.attempt_count).where(
            LifetimeRollup.rollup_key == LIFETIME_ROLLUP_KEY
        )
    ).scalar_one_or_none()

    return {
        "total_prisoners": total_prisoners,
        "active_prisoners": active_prisoners,
        "lifetime_attempts": current_attempts + int(lifetime_rollup_attempts or 0),
        "lifetime_credentials": current_credentials,
        "lifetime_commands": current_commands,
        "lifetime_downloads": current_downloads,
    }
