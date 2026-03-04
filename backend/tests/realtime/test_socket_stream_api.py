"""API-level tests for websocket sync lifecycle and live stream handoff."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import app.db.session as db_session_module
from app.models.lifetime_rollup import LifetimeRollup
from app.models.prisoner import Prisoner
from app.realtime.socket_server import realtime_event_bus

APPROVED_ORIGIN = "http://localhost:5173"


def _seed_snapshot_state() -> tuple[list[int], datetime]:
    anchor = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)
    shared_seen_at = anchor - timedelta(minutes=2)

    with db_session_module.SessionFactory() as session:
        first = Prisoner(
            source_ip="198.51.100.10",
            country_code="US",
            attempt_count=3,
            first_seen_at=anchor - timedelta(hours=3),
            last_seen_at=shared_seen_at,
            credential_count=2,
            command_count=1,
            download_count=0,
        )
        second = Prisoner(
            source_ip="198.51.100.20",
            country_code="AU",
            attempt_count=5,
            first_seen_at=anchor - timedelta(hours=2),
            last_seen_at=shared_seen_at,
            credential_count=3,
            command_count=2,
            download_count=1,
        )
        third = Prisoner(
            source_ip="198.51.100.30",
            country_code=None,
            attempt_count=2,
            first_seen_at=anchor - timedelta(hours=5),
            last_seen_at=anchor - timedelta(hours=1),
            credential_count=0,
            command_count=1,
            download_count=1,
        )
        session.add_all([first, second, third])
        session.flush()
        session.add(
            LifetimeRollup(
                rollup_key="overall",
                country_code=None,
                attempt_count=17,
                created_at=anchor - timedelta(days=1),
                updated_at=anchor - timedelta(days=1),
            )
        )
        session.commit()

        expected_order = [second.id, first.id, third.id]

    return expected_order, anchor


def _collect_sync_events(websocket) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    while True:
        message = websocket.receive_json()
        events.append(message)
        if message["event"] == "sync_complete":
            break
    return events


def _extract_snapshot_prisoner_ids(sync_events: list[dict[str, object]]) -> list[int]:
    snapshot_chunks = [event for event in sync_events if event["event"] == "snapshot_chunk"]
    assert len(snapshot_chunks) == 1
    return [row["prisoner_id"] for row in snapshot_chunks[0]["payload"]["prisoners"]]


def test_websocket_connect_emits_deterministic_sync_lifecycle_before_live_stream(
    client: TestClient,
) -> None:
    expected_snapshot_order, anchor = _seed_snapshot_state()

    with client.websocket_connect(
        "/ws/events",
        headers={"origin": APPROVED_ORIGIN},
    ) as websocket:
        first_sync_events = _collect_sync_events(websocket)
        assert [event["event"] for event in first_sync_events] == [
            "welcome",
            "sync_start",
            "snapshot_chunk",
            "stats_update",
            "sync_complete",
        ]

        sync_start = first_sync_events[1]["payload"]
        sync_chunk = first_sync_events[2]["payload"]
        sync_complete = first_sync_events[4]["payload"]
        assert sync_start["sync_id"] == sync_chunk["sync_id"] == sync_complete["sync_id"]

        assert _extract_snapshot_prisoner_ids(first_sync_events) == expected_snapshot_order

        stats_payload = first_sync_events[3]["payload"]
        assert stats_payload["total_prisoners"] == 3
        assert stats_payload["active_prisoners"] == 3
        assert stats_payload["lifetime_attempts"] == 27

        asyncio.run(
            realtime_event_bus.publish(
                "prisoner_updated",
                {
                    "prisoner_id": expected_snapshot_order[0],
                    "source_ip": "198.51.100.20",
                    "country_code": "AU",
                    "attempt_count": 6,
                    "first_seen_at": (anchor - timedelta(hours=2)).isoformat(),
                    "last_seen_at": anchor.isoformat(),
                    "credential_count": 3,
                    "command_count": 2,
                    "download_count": 1,
                    "enrichment": {
                        "status": "pending",
                        "last_updated_at": None,
                        "country_code": None,
                        "asn": None,
                        "reputation_severity": None,
                    },
                    "detail_sync_stale": True,
                    "detail_last_changed_at": anchor.isoformat(),
                },
            )
        )
        live_event = websocket.receive_json()
        assert live_event["event"] == "prisoner_updated"

    with client.websocket_connect(
        "/ws/events",
        headers={"origin": APPROVED_ORIGIN},
    ) as websocket:
        reconnect_events = _collect_sync_events(websocket)
        assert [event["event"] for event in reconnect_events] == [
            "welcome",
            "sync_start",
            "snapshot_chunk",
            "stats_update",
            "sync_complete",
        ]
        assert _extract_snapshot_prisoner_ids(reconnect_events) == expected_snapshot_order
