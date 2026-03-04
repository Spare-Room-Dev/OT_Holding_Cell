"""Periodic changed-only broadcaster for realtime aggregate stats."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.realtime_stats_service import build_realtime_stats_snapshot

logger = logging.getLogger(__name__)


class SupportsPublish(Protocol):
    async def publish(self, event: str, payload: dict[str, object]) -> object: ...


class RealtimeStatsBroadcaster:
    """Poll aggregate counters on a cadence and emit only changed stats snapshots."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        event_bus: SupportsPublish,
        cadence_ms: int | None = None,
    ) -> None:
        settings = get_settings()
        cadence = cadence_ms or settings.realtime_stats_cadence_ms
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._cadence_seconds = cadence / 1000
        self._last_emitted_snapshot: dict[str, int] | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if not self.is_running:
            return

        assert self._stop_event is not None
        assert self._task is not None

        self._stop_event.set()
        await self._task
        self._task = None
        self._stop_event = None

    async def publish_if_changed_once(self) -> bool:
        with self._session_factory() as session:
            snapshot = build_realtime_stats_snapshot(session=session)

        if snapshot == self._last_emitted_snapshot:
            return False

        payload = dict(snapshot)
        payload["changed"] = True
        await self._event_bus.publish("stats_update", payload)
        self._last_emitted_snapshot = snapshot
        return True

    async def _run_loop(self) -> None:
        assert self._stop_event is not None

        while not self._stop_event.is_set():
            try:
                await self.publish_if_changed_once()
            except Exception:
                logger.warning("Failed to broadcast realtime stats update", exc_info=True)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._cadence_seconds,
                )
            except asyncio.TimeoutError:
                continue
