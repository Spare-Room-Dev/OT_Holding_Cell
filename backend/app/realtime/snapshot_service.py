"""Authoritative reconnect snapshot assembly for websocket sync lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schemas.prisoners import PrisonerSummary
from app.services.prisoner_query_service import list_prisoners
from app.services.realtime_stats_service import build_realtime_stats_snapshot

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
        stats_payload={
            **build_realtime_stats_snapshot(session=session, now=now),
            "changed": True,
        },
    )
