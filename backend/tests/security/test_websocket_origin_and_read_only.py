"""Security tests for websocket origin controls and read-only inbound posture."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging

from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

import app.db.session as db_session_module
from app.models.prisoner import Prisoner
from app.realtime.socket_server import realtime_event_bus

APPROVED_ORIGIN = "http://localhost:5173"
BLOCKED_ORIGIN = "https://evil.example"


def _count_prisoners() -> int:
    with db_session_module.SessionFactory() as session:
        return int(session.query(Prisoner).count())


def _consume_sync_until_complete(websocket) -> list[str]:
    events: list[str] = []
    while True:
        payload = websocket.receive_json()
        events.append(payload["event"])
        if payload["event"] == "sync_complete":
            return events


def test_websocket_blocks_non_allowlisted_origin(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/events",
            headers={"origin": BLOCKED_ORIGIN},
        ):
            pass

    assert exc_info.value.code == 1008


def test_websocket_ignores_client_messages_and_keeps_stream_read_only(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with db_session_module.SessionFactory() as session:
        session.add(
            Prisoner(
                source_ip="198.51.100.80",
                country_code="US",
                attempt_count=1,
                first_seen_at=datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc),
                last_seen_at=datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc),
                credential_count=0,
                command_count=0,
                download_count=0,
            )
        )
        session.commit()

    before_count = _count_prisoners()
    caplog.set_level(logging.INFO, logger="app.realtime.socket_server")

    with client.websocket_connect(
        "/ws/events",
        headers={"origin": APPROVED_ORIGIN},
    ) as websocket:
        lifecycle_events = _consume_sync_until_complete(websocket)
        assert lifecycle_events[0] == "welcome"
        assert lifecycle_events[-1] == "sync_complete"

        websocket.send_json({"event": "attempt_mutation", "payload": {"source_ip": "203.0.113.44"}})

        asyncio.run(
            realtime_event_bus.publish(
                "stats_update",
                {
                    "total_prisoners": 1,
                    "active_prisoners": 1,
                    "lifetime_attempts": 1,
                    "lifetime_credentials": 0,
                    "lifetime_commands": 0,
                    "lifetime_downloads": 0,
                    "changed": False,
                },
            )
        )

        outbound = websocket.receive_json()
        assert outbound["event"] == "stats_update"

    after_count = _count_prisoners()
    assert after_count == before_count

    ignored_logs = [record for record in caplog.records if record.message == "ignored_client_ws_message"]
    assert ignored_logs
    assert ignored_logs[-1].origin == APPROVED_ORIGIN
    assert ignored_logs[-1].frame_type == "text"
