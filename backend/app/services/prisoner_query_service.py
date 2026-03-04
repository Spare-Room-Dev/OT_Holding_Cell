"""Prisoner query service for deterministic cursor pagination."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.prisoner_command import PrisonerCommand
from app.models.prisoner_credential import PrisonerCredential
from app.models.prisoner_download import PrisonerDownload
from app.models.prisoner_protocol_activity import PrisonerProtocolActivity
from app.models.prisoner import Prisoner
from app.schemas.prisoners import (
    PrisonerCommandHistoryEntry,
    PrisonerCredentialHistoryEntry,
    PrisonerDetailPrisoner,
    PrisonerDetailResponse,
    PrisonerDownloadHistoryEntry,
    PrisonerEnrichmentDetail,
    PrisonerEnrichmentGeo,
    PrisonerEnrichmentReputation,
    PrisonerEnrichmentSummary,
    PrisonerListResponse,
    PrisonerProtocolHistoryEntry,
    PrisonerSummary,
)


class InvalidCursorTokenError(ValueError):
    """Raised when a cursor token cannot be decoded."""


@dataclass(frozen=True)
class CursorPosition:
    """Decoded keyset cursor position."""

    last_seen_at: datetime
    prisoner_id: int


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_optional_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _coerce_utc(value)


def encode_prisoner_cursor(*, last_seen_at: datetime, prisoner_id: int) -> str:
    """Encode keyset position into an opaque cursor token."""

    payload = {
        "last_seen_at": _coerce_utc(last_seen_at).isoformat(),
        "id": prisoner_id,
    }
    serialized = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(serialized).decode("ascii")


def decode_prisoner_cursor(cursor_token: str) -> CursorPosition:
    """Decode and validate prisoner cursor token payload."""

    try:
        decoded = base64.urlsafe_b64decode(cursor_token.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        last_seen_at_raw = payload["last_seen_at"]
        prisoner_id_raw = payload["id"]
        last_seen_at = datetime.fromisoformat(last_seen_at_raw)
        prisoner_id = int(prisoner_id_raw)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise InvalidCursorTokenError("Invalid cursor token") from None

    if prisoner_id < 1:
        raise InvalidCursorTokenError("Invalid cursor token")

    return CursorPosition(
        last_seen_at=_coerce_utc(last_seen_at),
        prisoner_id=prisoner_id,
    )


def _build_prisoner_summary(prisoner: Prisoner) -> PrisonerSummary:
    return PrisonerSummary(
        id=prisoner.id,
        source_ip=prisoner.source_ip,
        country_code=prisoner.country_code,
        attempt_count=prisoner.attempt_count,
        first_seen_at=prisoner.first_seen_at,
        last_seen_at=prisoner.last_seen_at,
        credential_count=prisoner.credential_count,
        command_count=prisoner.command_count,
        download_count=prisoner.download_count,
        enrichment=_build_prisoner_enrichment_summary(prisoner),
    )


def _build_prisoner_enrichment_summary(prisoner: Prisoner) -> PrisonerEnrichmentSummary:
    return PrisonerEnrichmentSummary(
        status=prisoner.enrichment_status,
        last_updated_at=_coerce_optional_utc(prisoner.last_enriched_at),
        country_code=prisoner.enrichment_country_code,
        asn=prisoner.enrichment_asn,
        reputation_severity=prisoner.enrichment_reputation_severity,
    )


def _build_prisoner_enrichment_detail(prisoner: Prisoner) -> PrisonerEnrichmentDetail:
    raw_reason_metadata = prisoner.enrichment_reason_metadata or {}
    reason_metadata = {
        str(key): str(value)
        for key, value in raw_reason_metadata.items()
    }
    return PrisonerEnrichmentDetail(
        status=prisoner.enrichment_status,
        last_updated_at=_coerce_optional_utc(prisoner.last_enriched_at),
        provider=prisoner.enrichment_provider,
        geo=PrisonerEnrichmentGeo(
            country_code=prisoner.enrichment_country_code,
            asn=prisoner.enrichment_asn,
        ),
        reputation=PrisonerEnrichmentReputation(
            severity=prisoner.enrichment_reputation_severity,
            confidence=prisoner.enrichment_reputation_confidence,
        ),
        reason_metadata=reason_metadata,
    )


def list_prisoners(
    *,
    session: Session,
    limit: int,
    cursor: str | None = None,
    country: str | None = None,
) -> PrisonerListResponse:
    """Return a deterministic prisoner summary page with an opaque cursor."""

    statement = select(Prisoner)

    if country is not None:
        normalized_country = country.strip()
        if normalized_country.lower() == "unknown":
            statement = statement.where(Prisoner.country_code.is_(None))
        else:
            statement = statement.where(Prisoner.country_code == normalized_country.upper())

    if cursor:
        cursor_position = decode_prisoner_cursor(cursor)
        statement = statement.where(
            or_(
                Prisoner.last_seen_at < cursor_position.last_seen_at,
                and_(
                    Prisoner.last_seen_at == cursor_position.last_seen_at,
                    Prisoner.id < cursor_position.prisoner_id,
                ),
            )
        )

    rows = session.execute(
        statement
        .order_by(Prisoner.last_seen_at.desc(), Prisoner.id.desc())
        .limit(limit + 1)
    ).scalars().all()

    has_more = len(rows) > limit
    page_rows = rows[:limit]

    next_cursor: str | None = None
    if has_more and page_rows:
        last_row = page_rows[-1]
        next_cursor = encode_prisoner_cursor(
            last_seen_at=last_row.last_seen_at,
            prisoner_id=last_row.id,
        )

    return PrisonerListResponse(
        items=[_build_prisoner_summary(row) for row in page_rows],
        next_cursor=next_cursor,
    )


def get_prisoner_summary(*, session: Session, prisoner_id: int) -> PrisonerSummary | None:
    """Return one canonical prisoner summary row for realtime mutation events."""

    prisoner = session.execute(
        select(Prisoner).where(Prisoner.id == prisoner_id)
    ).scalar_one_or_none()
    if prisoner is None:
        return None
    return _build_prisoner_summary(prisoner)


def get_prisoner_detail(*, session: Session, prisoner_id: int) -> PrisonerDetailResponse | None:
    """Return sectioned persisted history for a single prisoner."""

    prisoner = session.execute(
        select(Prisoner).where(Prisoner.id == prisoner_id)
    ).scalar_one_or_none()
    if prisoner is None:
        return None

    protocol_rows = session.execute(
        select(PrisonerProtocolActivity)
        .where(PrisonerProtocolActivity.prisoner_id == prisoner.id)
        .order_by(
            PrisonerProtocolActivity.last_seen_at.desc(),
            PrisonerProtocolActivity.id.desc(),
        )
    ).scalars().all()
    credential_rows = session.execute(
        select(PrisonerCredential)
        .where(PrisonerCredential.prisoner_id == prisoner.id)
        .order_by(PrisonerCredential.observed_at.desc(), PrisonerCredential.id.desc())
    ).scalars().all()
    command_rows = session.execute(
        select(PrisonerCommand)
        .where(PrisonerCommand.prisoner_id == prisoner.id)
        .order_by(PrisonerCommand.observed_at.desc(), PrisonerCommand.id.desc())
    ).scalars().all()
    download_rows = session.execute(
        select(PrisonerDownload)
        .where(PrisonerDownload.prisoner_id == prisoner.id)
        .order_by(PrisonerDownload.observed_at.desc(), PrisonerDownload.id.desc())
    ).scalars().all()

    return PrisonerDetailResponse(
        prisoner=PrisonerDetailPrisoner(
            id=prisoner.id,
            source_ip=prisoner.source_ip,
            country_code=prisoner.country_code,
            attempt_count=prisoner.attempt_count,
            first_seen_at=prisoner.first_seen_at,
            last_seen_at=prisoner.last_seen_at,
            credential_count=prisoner.credential_count,
            command_count=prisoner.command_count,
            download_count=prisoner.download_count,
            enrichment=_build_prisoner_enrichment_detail(prisoner),
        ),
        protocol_history=[
            PrisonerProtocolHistoryEntry(
                protocol=row.protocol,
                attempt_count=row.attempt_count,
                first_seen_at=row.first_seen_at,
                last_seen_at=row.last_seen_at,
            )
            for row in protocol_rows
        ],
        credentials=[
            PrisonerCredentialHistoryEntry(
                protocol=row.protocol,
                credential=row.credential,
                observed_at=row.observed_at,
            )
            for row in credential_rows
        ],
        commands=[
            PrisonerCommandHistoryEntry(
                protocol=row.protocol,
                command=row.command,
                observed_at=row.observed_at,
            )
            for row in command_rows
        ],
        downloads=[
            PrisonerDownloadHistoryEntry(
                protocol=row.protocol,
                download_url=row.download_url,
                observed_at=row.observed_at,
            )
            for row in download_rows
        ],
    )
