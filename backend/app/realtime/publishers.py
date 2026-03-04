"""Reusable realtime publishers for prisoner lifecycle mutation events."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.realtime.event_bus import RealtimeEventBus, get_realtime_event_bus
from app.schemas.prisoners import PrisonerSummary
from app.services.prisoner_query_service import get_prisoner_summary

logger = logging.getLogger(__name__)

PrisonerLifecycleEventName = Literal["new_prisoner", "prisoner_updated", "prisoner_enriched"]


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _default_detail_last_changed_at(*, last_seen_at: datetime, enrichment_last_updated_at: datetime | None) -> datetime:
    timestamps = [_coerce_utc(last_seen_at)]
    if enrichment_last_updated_at is not None:
        timestamps.append(_coerce_utc(enrichment_last_updated_at))
    return max(timestamps)


def build_prisoner_realtime_payload(
    *,
    prisoner_summary: PrisonerSummary,
    detail_sync_stale: bool = True,
    detail_last_changed_at: datetime | None = None,
) -> dict[str, object]:
    """Map canonical prisoner summaries to realtime payload schema."""

    payload = prisoner_summary.model_dump(mode="python")
    payload["prisoner_id"] = payload.pop("id")
    payload["detail_sync_stale"] = detail_sync_stale
    payload["detail_last_changed_at"] = detail_last_changed_at or _default_detail_last_changed_at(
        last_seen_at=prisoner_summary.last_seen_at,
        enrichment_last_updated_at=prisoner_summary.enrichment.last_updated_at,
    )
    return payload


def _publish_in_event_loop(
    *,
    event_bus: RealtimeEventBus,
    event_name: PrisonerLifecycleEventName,
    payload: dict[str, object],
) -> None:
    async def _publish() -> None:
        await event_bus.publish(event_name, payload)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_publish())
        return

    task = loop.create_task(_publish())

    def _log_publish_error(completed_task: asyncio.Task[None]) -> None:
        try:
            completed_task.result()
        except Exception:
            logger.warning(
                "Realtime publish failed for event=%s prisoner_id=%s",
                event_name,
                payload.get("prisoner_id"),
                exc_info=True,
            )

    task.add_done_callback(_log_publish_error)


def publish_prisoner_lifecycle_event(
    *,
    session: Session,
    event_bus: RealtimeEventBus,
    event_name: PrisonerLifecycleEventName,
    prisoner_id: int,
) -> bool:
    """Publish canonical prisoner lifecycle events using full-summary payloads."""

    prisoner_summary = get_prisoner_summary(session=session, prisoner_id=prisoner_id)
    if prisoner_summary is None:
        return False

    payload = build_prisoner_realtime_payload(prisoner_summary=prisoner_summary)
    _publish_in_event_loop(
        event_bus=event_bus,
        event_name=event_name,
        payload=payload,
    )
    return True
