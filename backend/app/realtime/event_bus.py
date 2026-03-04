"""In-process fanout bus for typed realtime events."""

from __future__ import annotations

from datetime import datetime, timezone
import inspect
from itertools import count
from typing import Any, Awaitable, Callable, Dict, Optional, Union
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.realtime import RealtimeEventEnvelope, RealtimeEventName

RealtimeSubscriber = Callable[[RealtimeEventEnvelope], Union[None, Awaitable[None]]]


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _default_event_id_factory(_sequence: int) -> str:
    return f"evt-{uuid4().hex}"


class RealtimeEventBus:
    """Single-process publish/subscribe bus for schema-validated realtime events."""

    def __init__(
        self,
        protocol_version: Optional[str] = None,
        clock: Optional[Callable[[], datetime]] = None,
        event_id_factory: Optional[Callable[[int], str]] = None,
    ) -> None:
        settings = get_settings()
        self._protocol_version = protocol_version or settings.realtime_protocol_version
        self._clock = clock or _default_clock
        self._event_id_factory = event_id_factory or _default_event_id_factory
        self._publish_sequence = 0
        self._subscriber_tokens = count(1)
        self._subscribers: Dict[int, RealtimeSubscriber] = {}

    def subscribe(self, subscriber: RealtimeSubscriber) -> int:
        """Register a subscriber callback and return an unsubscribe token."""

        token = next(self._subscriber_tokens)
        self._subscribers[token] = subscriber
        return token

    def unsubscribe(self, token: int) -> None:
        """Remove a subscriber token if present."""

        self._subscribers.pop(token, None)

    async def publish(self, event: RealtimeEventName, payload: Dict[str, Any]) -> RealtimeEventEnvelope:
        """Publish a typed realtime event and fan it out to all subscribers."""

        self._publish_sequence += 1
        sequence = self._publish_sequence
        occurred_at = self._normalize_clock_timestamp(self._clock())

        envelope = RealtimeEventEnvelope(
            event_id=self._event_id_factory(sequence),
            event=event,
            occurred_at=occurred_at,
            protocol_version=self._protocol_version,
            payload=self._attach_ordering(
                event=event,
                payload=payload,
                sequence=sequence,
                occurred_at=occurred_at,
            ),
        )
        await self._fanout(envelope)
        return envelope

    async def _fanout(self, envelope: RealtimeEventEnvelope) -> None:
        for subscriber in list(self._subscribers.values()):
            result = subscriber(envelope)
            if inspect.isawaitable(result):
                await result

    @staticmethod
    def _normalize_clock_timestamp(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("clock must return timezone-aware timestamps")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _attach_ordering(
        event: RealtimeEventName,
        payload: Dict[str, Any],
        sequence: int,
        occurred_at: datetime,
    ) -> Dict[str, Any]:
        payload_with_ordering = dict(payload)
        ordering = dict(payload_with_ordering.get("ordering", {}))
        ordering.setdefault("publish_sequence", sequence)
        ordering.setdefault("source_updated_at", occurred_at)
        payload_with_ordering["ordering"] = ordering

        if event == "welcome" and "server_time" not in payload_with_ordering:
            payload_with_ordering["server_time"] = occurred_at

        return payload_with_ordering
