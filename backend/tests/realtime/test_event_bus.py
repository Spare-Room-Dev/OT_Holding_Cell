"""Behavioral tests for the in-process realtime fanout bus."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.realtime.event_bus import RealtimeEventBus


def test_event_bus_fanout_preserves_publish_order() -> None:
    async def scenario() -> None:
        base_time = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)
        tick = {"count": 0}

        def clock() -> datetime:
            value = base_time + timedelta(seconds=tick["count"])
            tick["count"] += 1
            return value

        bus = RealtimeEventBus(
            protocol_version="v1",
            clock=clock,
            event_id_factory=lambda sequence: f"evt-{sequence:04d}",
        )
        received_primary: list[tuple[str, int]] = []
        received_secondary: list[tuple[str, int]] = []

        async def subscriber_primary(event) -> None:
            received_primary.append((event.event, event.payload.ordering.publish_sequence))

        async def subscriber_secondary(event) -> None:
            received_secondary.append((event.event, event.payload.ordering.publish_sequence))

        bus.subscribe(subscriber_primary)
        bus.subscribe(subscriber_secondary)

        await bus.publish(
            "welcome",
            {
                "server_time": base_time.isoformat(),
            },
        )
        await bus.publish(
            "stats_update",
            {
                "total_prisoners": 3,
                "active_prisoners": 2,
                "lifetime_attempts": 9,
                "lifetime_credentials": 5,
                "lifetime_commands": 3,
                "lifetime_downloads": 1,
                "changed": True,
            },
        )

        assert received_primary == [("welcome", 1), ("stats_update", 2)]
        assert received_secondary == [("welcome", 1), ("stats_update", 2)]

    asyncio.run(scenario())


def test_event_bus_unsubscribe_stops_delivery() -> None:
    async def scenario() -> None:
        bus = RealtimeEventBus(protocol_version="v1")
        deliveries: list[str] = []

        async def subscriber(event) -> None:
            deliveries.append(event.event)

        token = bus.subscribe(subscriber)
        bus.unsubscribe(token)

        await bus.publish(
            "stats_update",
            {
                "total_prisoners": 0,
                "active_prisoners": 0,
                "lifetime_attempts": 0,
                "lifetime_credentials": 0,
                "lifetime_commands": 0,
                "lifetime_downloads": 0,
                "changed": False,
            },
        )

        assert deliveries == []

    asyncio.run(scenario())
