"""Transactional ingest processing with replay-safe idempotency."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ingest_delivery import IngestDelivery
from app.models.prisoner import Prisoner
from app.models.prisoner_protocol_activity import PrisonerProtocolActivity
from app.schemas.ingest import IngestPayload


def _coerce_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _update_seen_window(*, first_seen_at: datetime, last_seen_at: datetime, observed_at: datetime) -> tuple[datetime, datetime]:
    normalized_first = _coerce_utc(first_seen_at)
    normalized_last = _coerce_utc(last_seen_at)
    normalized_observed = _coerce_utc(observed_at)

    first_seen = min(normalized_first, normalized_observed)
    last_seen = max(normalized_last, normalized_observed)
    return first_seen, last_seen


def _apply_prisoner_observation(prisoner: Prisoner, payload: IngestPayload) -> None:
    prisoner.attempt_count += 1
    prisoner.first_seen_at, prisoner.last_seen_at = _update_seen_window(
        first_seen_at=prisoner.first_seen_at,
        last_seen_at=prisoner.last_seen_at,
        observed_at=payload.timestamp,
    )
    prisoner.credential_count += len(payload.credentials)
    prisoner.command_count += len(payload.commands)
    prisoner.download_count += len(payload.downloads)


def _apply_protocol_activity_observation(
    protocol_activity: PrisonerProtocolActivity,
    payload: IngestPayload,
) -> None:
    protocol_activity.attempt_count += 1
    protocol_activity.first_seen_at, protocol_activity.last_seen_at = _update_seen_window(
        first_seen_at=protocol_activity.first_seen_at,
        last_seen_at=protocol_activity.last_seen_at,
        observed_at=payload.timestamp,
    )


def process_ingest_payload(*, payload: IngestPayload, source_ip: str, session: Session) -> dict[str, object]:
    """Register delivery once, then mutate prisoner state only for first-time delivery IDs."""

    delivery = IngestDelivery.from_payload(
        delivery_id=payload.delivery_id,
        protocol=payload.protocol,
        source_ip=source_ip,
    )
    session.add(delivery)

    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return {
            "status": "duplicate_ignored",
            "delivery_id": str(payload.delivery_id),
        }

    prisoner = session.execute(
        select(Prisoner).where(
            Prisoner.source_ip == source_ip,
        )
    ).scalar_one_or_none()

    outcome = "created"
    if prisoner is None:
        prisoner = Prisoner(
            source_ip=source_ip,
            attempt_count=1,
            first_seen_at=payload.timestamp,
            last_seen_at=payload.timestamp,
            credential_count=len(payload.credentials),
            command_count=len(payload.commands),
            download_count=len(payload.downloads),
        )
        session.add(prisoner)
        session.flush()
    else:
        outcome = "updated"
        _apply_prisoner_observation(prisoner, payload)

    protocol_activity = session.execute(
        select(PrisonerProtocolActivity).where(
            PrisonerProtocolActivity.prisoner_id == prisoner.id,
            PrisonerProtocolActivity.protocol == payload.protocol,
        )
    ).scalar_one_or_none()
    if protocol_activity is None:
        protocol_activity = PrisonerProtocolActivity(
            prisoner_id=prisoner.id,
            protocol=payload.protocol,
            attempt_count=1,
            first_seen_at=payload.timestamp,
            last_seen_at=payload.timestamp,
        )
        session.add(protocol_activity)
    else:
        _apply_protocol_activity_observation(protocol_activity, payload)

    delivery.prisoner_id = prisoner.id
    session.commit()

    return {
        "status": "processed",
        "delivery_id": str(payload.delivery_id),
        "outcome": outcome,
        "prisoner_id": prisoner.id,
    }
