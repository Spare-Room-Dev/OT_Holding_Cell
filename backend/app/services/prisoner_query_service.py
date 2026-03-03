"""Prisoner query service for deterministic cursor pagination."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.prisoner import Prisoner
from app.schemas.prisoners import PrisonerListResponse, PrisonerSummary


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
        items=[
            PrisonerSummary(
                id=row.id,
                source_ip=row.source_ip,
                country_code=row.country_code,
                attempt_count=row.attempt_count,
                first_seen_at=row.first_seen_at,
                last_seen_at=row.last_seen_at,
                credential_count=row.credential_count,
                command_count=row.command_count,
                download_count=row.download_count,
            )
            for row in page_rows
        ],
        next_cursor=next_cursor,
    )
