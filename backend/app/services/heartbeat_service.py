"""Heartbeat persistence and stale-window liveness evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forwarder_heartbeat import ForwarderHeartbeat
def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def record_heartbeat(
    *,
    protocol: str,
    observed_at: datetime,
    source_ip: str,
    warning_window_seconds: int,
    session: Session,
) -> dict[str, object]:
    """Persist heartbeat and report freshness for operator liveness checks."""

    existing = session.execute(
        select(ForwarderHeartbeat).where(
            ForwarderHeartbeat.source_ip == source_ip,
            ForwarderHeartbeat.protocol == protocol,
        )
    ).scalar_one_or_none()

    heartbeat_timestamp = _as_utc(observed_at)
    now_utc = datetime.now(timezone.utc)

    if existing is None:
        record = ForwarderHeartbeat(
            source_ip=source_ip,
            protocol=protocol,
            last_seen_at=heartbeat_timestamp,
            created_at=now_utc,
            updated_at=now_utc,
        )
        session.add(record)
        session.flush()
    else:
        record = existing
        record.last_seen_at = heartbeat_timestamp
        record.updated_at = now_utc

    session.commit()
    session.refresh(record)

    last_seen_at = _as_utc(record.last_seen_at)
    is_stale = (now_utc - last_seen_at).total_seconds() > warning_window_seconds

    return {
        "status": "ok",
        "protocol": protocol,
        "source_ip": source_ip,
        "last_seen_at": last_seen_at.isoformat(),
        "is_stale": is_stale,
        "stale_after_seconds": warning_window_seconds,
    }
