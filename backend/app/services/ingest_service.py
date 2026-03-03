"""Transactional ingest processing with replay-safe idempotency."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Union

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.ingest_delivery import IngestDelivery
from app.models.prisoner import Prisoner
from app.models.prisoner_command import PrisonerCommand
from app.models.prisoner_credential import PrisonerCredential
from app.models.prisoner_download import PrisonerDownload
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


def _mask_credential(raw_credential: str) -> str:
    username, delimiter, _secret = raw_credential.partition(":")
    if delimiter:
        return f"{username}:{'*' * 8}"

    visible_prefix = raw_credential[:2]
    masked_length = max(len(raw_credential) - len(visible_prefix), 2)
    return f"{visible_prefix}{'*' * masked_length}"


def _append_detail_history(*, prisoner_id: int, payload: IngestPayload, session: Session) -> None:
    for credential in payload.credentials:
        session.add(
            PrisonerCredential(
                prisoner_id=prisoner_id,
                protocol=payload.protocol,
                credential=_mask_credential(credential),
                observed_at=payload.timestamp,
            )
        )

    for command_text in payload.commands:
        session.add(
            PrisonerCommand(
                prisoner_id=prisoner_id,
                protocol=payload.protocol,
                command=command_text,
                observed_at=payload.timestamp,
            )
        )

    for download_url in payload.downloads:
        session.add(
            PrisonerDownload(
                prisoner_id=prisoner_id,
                protocol=payload.protocol,
                download_url=download_url,
                observed_at=payload.timestamp,
            )
        )

    session.flush()


HistoryModel = Union[type[PrisonerCredential], type[PrisonerCommand], type[PrisonerDownload]]


def _prune_history(*, prisoner_id: int, cap: int, model: HistoryModel, session: Session) -> None:
    total_rows = session.execute(
        select(func.count(model.id)).where(model.prisoner_id == prisoner_id)
    ).scalar_one()
    if total_rows <= cap:
        return

    rows_to_prune = total_rows - cap
    oldest_ids = session.execute(
        select(model.id)
        .where(model.prisoner_id == prisoner_id)
        .order_by(model.observed_at.asc(), model.id.asc())
        .limit(rows_to_prune)
    ).scalars().all()
    if not oldest_ids:
        return

    session.execute(
        delete(model).where(model.id.in_(oldest_ids))
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

    settings = get_settings()
    _append_detail_history(prisoner_id=prisoner.id, payload=payload, session=session)
    _prune_history(
        prisoner_id=prisoner.id,
        cap=settings.credential_history_cap,
        model=PrisonerCredential,
        session=session,
    )
    _prune_history(
        prisoner_id=prisoner.id,
        cap=settings.command_history_cap,
        model=PrisonerCommand,
        session=session,
    )
    _prune_history(
        prisoner_id=prisoner.id,
        cap=settings.download_history_cap,
        model=PrisonerDownload,
        session=session,
    )

    delivery.prisoner_id = prisoner.id
    session.commit()

    return {
        "status": "processed",
        "delivery_id": str(payload.delivery_id),
        "outcome": outcome,
        "prisoner_id": prisoner.id,
    }
