"""Heartbeat persistence and stale-window liveness evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forwarder_heartbeat import ForwarderHeartbeat
from app.schemas.heartbeat import HeartbeatPayload


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def process_heartbeat_payload(
    *,
    payload: HeartbeatPayload,
    source_ip: str,
    stale_warning_seconds: int,
    session: Session,
) -> dict[str, object]:
    """Persist heartbeat and report freshness for operator liveness checks."""

    existing = session.execute(
        select(ForwarderHeartbeat).where(
            ForwarderHeartbeat.source_ip == source_ip,
            ForwarderHeartbeat.protocol == payload.protocol,
        )
    ).scalar_one_or_none()

    heartbeat_timestamp = _as_utc(payload.timestamp)
    now_utc = datetime.now(timezone.utc)

    if existing is None:
        record = ForwarderHeartbeat(
            source_ip=source_ip,
            protocol=payload.protocol,
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
    is_stale = (now_utc - last_seen_at).total_seconds() > stale_warning_seconds

    return {
        "status": "ok",
        "protocol": payload.protocol,
        "source_ip": source_ip,
        "last_seen_at": last_seen_at.isoformat(),
        "is_stale": is_stale,
        "stale_after_seconds": stale_warning_seconds,
    }
