"""Transactional ingest processing with replay-safe idempotency."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ingest_delivery import IngestDelivery
from app.models.prisoner import Prisoner
from app.schemas.ingest import IngestPayload


def _apply_prisoner_observation(prisoner: Prisoner, payload: IngestPayload) -> None:
    prisoner.last_seen_at = payload.timestamp
    prisoner.credential_count += len(payload.credentials)
    prisoner.command_count += len(payload.commands)
    prisoner.download_count += len(payload.downloads)


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
            Prisoner.protocol == payload.protocol,
        )
    ).scalar_one_or_none()

    outcome = "updated"
    if prisoner is None:
        prisoner = Prisoner(
            source_ip=source_ip,
            protocol=payload.protocol,
            first_seen_at=payload.timestamp,
            last_seen_at=payload.timestamp,
            credential_count=len(payload.credentials),
            command_count=len(payload.commands),
            download_count=len(payload.downloads),
        )
        session.add(prisoner)
        session.flush()
        outcome = "created"
    else:
        _apply_prisoner_observation(prisoner, payload)

    delivery.prisoner_id = prisoner.id
    session.commit()

    return {
        "status": "processed",
        "delivery_id": str(payload.delivery_id),
        "outcome": outcome,
        "prisoner_id": prisoner.id,
    }
