"""Authoritative reconnect snapshot assembly for websocket sync lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.lifetime_rollup import LifetimeRollup
from app.models.prisoner import Prisoner
from app.schemas.prisoners import PrisonerSummary
from app.services.prisoner_query_service import list_prisoners

ACTIVE_WINDOW_HOURS = 24
LIFETIME_ROLLUP_KEY = "overall"
SNAPSHOT_PAGE_LIMIT = 200


@dataclass(frozen=True)
class SnapshotChunk:
    chunk_index: int
    total_chunks: int
    prisoners: list[dict[str, object]]


@dataclass(frozen=True)
class RealtimeSnapshot:
    chunks: list[SnapshotChunk]
    stats_payload: dict[str, object]


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _summary_to_snapshot_payload(
    summary: PrisonerSummary,
    *,
    ordering_sequence: int,
) -> dict[str, object]:
    detail_last_changed_at = _coerce_utc(summary.last_seen_at)
    enrichment_last_updated = summary.enrichment.last_updated_at
    if enrichment_last_updated is not None:
        detail_last_changed_at = max(
            detail_last_changed_at,
            _coerce_utc(enrichment_last_updated),
        )

    return {
        "ordering": {
            "publish_sequence": ordering_sequence,
            "source_updated_at": detail_last_changed_at,
        },
        "prisoner_id": summary.id,
        "source_ip": summary.source_ip,
        "country_code": summary.country_code,
        "attempt_count": summary.attempt_count,
        "first_seen_at": _coerce_utc(summary.first_seen_at),
        "last_seen_at": _coerce_utc(summary.last_seen_at),
        "credential_count": summary.credential_count,
        "command_count": summary.command_count,
        "download_count": summary.download_count,
        "enrichment": summary.enrichment.model_dump(mode="json"),
        "detail_sync_stale": False,
        "detail_last_changed_at": detail_last_changed_at,
    }


def _load_all_prisoner_summaries(*, session: Session) -> list[PrisonerSummary]:
    cursor: str | None = None
    summaries: list[PrisonerSummary] = []

    while True:
        page = list_prisoners(
            session=session,
            limit=SNAPSHOT_PAGE_LIMIT,
            cursor=cursor,
        )
        summaries.extend(page.items)
        if page.next_cursor is None:
            return summaries
        cursor = page.next_cursor


def _build_stats_payload(*, session: Session, now: datetime) -> dict[str, object]:
    active_cutoff = now - timedelta(hours=ACTIVE_WINDOW_HOURS)

    total_prisoners = int(
        session.execute(select(func.count(Prisoner.id))).scalar_one()
    )
    active_prisoners = int(
        session.execute(
            select(func.count(Prisoner.id)).where(Prisoner.last_seen_at >= active_cutoff)
        ).scalar_one()
    )

    current_attempts = int(
        session.execute(select(func.coalesce(func.sum(Prisoner.attempt_count), 0))).scalar_one()
    )
    current_credentials = int(
        session.execute(select(func.coalesce(func.sum(Prisoner.credential_count), 0))).scalar_one()
    )
    current_commands = int(
        session.execute(select(func.coalesce(func.sum(Prisoner.command_count), 0))).scalar_one()
    )
    current_downloads = int(
        session.execute(select(func.coalesce(func.sum(Prisoner.download_count), 0))).scalar_one()
    )

    lifetime_rollup_attempts = session.execute(
        select(LifetimeRollup.attempt_count).where(LifetimeRollup.rollup_key == LIFETIME_ROLLUP_KEY)
    ).scalar_one_or_none()
    lifetime_attempts = current_attempts + int(lifetime_rollup_attempts or 0)

    return {
        "total_prisoners": total_prisoners,
        "active_prisoners": active_prisoners,
        "lifetime_attempts": lifetime_attempts,
        "lifetime_credentials": current_credentials,
        "lifetime_commands": current_commands,
        "lifetime_downloads": current_downloads,
        "changed": True,
    }


def build_authoritative_snapshot(
    *,
    session: Session,
    chunk_size: int = SNAPSHOT_PAGE_LIMIT,
) -> RealtimeSnapshot:
    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than zero")

    now = datetime.now(timezone.utc)
    summaries = _load_all_prisoner_summaries(session=session)
    prisoners = [
        _summary_to_snapshot_payload(summary, ordering_sequence=index)
        for index, summary in enumerate(summaries, start=1)
    ]

    total_chunks = (len(prisoners) + chunk_size - 1) // chunk_size
    chunks: list[SnapshotChunk] = []
    for index, start in enumerate(range(0, len(prisoners), chunk_size), start=1):
        chunks.append(
            SnapshotChunk(
                chunk_index=index,
                total_chunks=total_chunks,
                prisoners=prisoners[start : start + chunk_size],
            )
        )

    return RealtimeSnapshot(
        chunks=chunks,
        stats_payload=_build_stats_payload(session=session, now=now),
    )
