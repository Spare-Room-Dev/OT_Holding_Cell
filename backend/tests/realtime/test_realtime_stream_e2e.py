"""End-to-end websocket stream tests for reconnect and live continuity."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

import app.db.session as db_session_module
from app.core.config import get_settings
from app.db.session import create_session_factory
from app.main import create_app
from app.models.lifetime_rollup import LifetimeRollup
from app.models.prisoner import Prisoner
from app.realtime.publishers import get_realtime_event_bus
from app.realtime.socket_server import realtime_event_bus

APPROVED_ORIGIN = "http://localhost:5173"


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _build_client(
    *,
    database_url: str,
    monkeypatch,
) -> TestClient:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", "current-forwarder-key")
    monkeypatch.setenv("INGEST_API_KEY_PREVIOUS", "previous-forwarder-key")
    monkeypatch.setenv("ALLOWED_FORWARDER_IPS", "[\"203.0.113.10\", \"127.0.0.1\"]")
    monkeypatch.setenv("INGEST_RATE_LIMIT_MAX_REQUESTS", "100")
    monkeypatch.setenv("INGEST_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("HEARTBEAT_RATE_LIMIT_MAX_REQUESTS", "100")
    monkeypatch.setenv("HEARTBEAT_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("HEARTBEAT_STALE_WARNING_SECONDS", "60")
    monkeypatch.setenv("REALTIME_STATS_CADENCE_MS", "20")

    get_settings.cache_clear()
    db_session_module.SessionFactory = create_session_factory(database_url)
    return TestClient(create_app())


def _collect_sync_events(websocket) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    while True:
        message = websocket.receive_json()
        events.append(message)
        if message["event"] == "sync_complete":
            break
    return events


def _seed_initial_snapshot_state(*, anchor: datetime) -> int:
    with db_session_module.SessionFactory() as session:
        prisoner = Prisoner(
            source_ip="198.51.100.5",
            country_code="US",
            attempt_count=2,
            first_seen_at=anchor - timedelta(hours=3),
            last_seen_at=anchor - timedelta(minutes=10),
            credential_count=1,
            command_count=1,
            download_count=0,
        )
        session.add(prisoner)
        session.flush()
        session.add(
            LifetimeRollup(
                rollup_key="overall",
                country_code=None,
                attempt_count=8,
                created_at=anchor - timedelta(days=1),
                updated_at=anchor - timedelta(days=1),
            )
        )
        session.commit()
        return prisoner.id


def test_app_lifespan_starts_and_stops_stats_broadcaster(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'stream-lifespan.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    client = _build_client(database_url=database_url, monkeypatch=monkeypatch)
    app = client.app

    with client:
        broadcaster = app.state.stats_broadcaster
        assert broadcaster.is_running is True

    assert app.state.stats_broadcaster.is_running is False


def test_realtime_stream_e2e_reconnect_snapshot_then_live_prisoner_and_stats_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'stream-e2e.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")
    anchor = datetime(2026, 3, 4, 15, 0, tzinfo=timezone.utc)
    seeded_prisoner_id = _seed_initial_snapshot_state(anchor=anchor)

    assert realtime_event_bus is get_realtime_event_bus()

    client = _build_client(database_url=database_url, monkeypatch=monkeypatch)
    with client:
        with client.websocket_connect(
            "/ws/events",
            headers={"origin": APPROVED_ORIGIN},
        ) as websocket:
            sync_events = _collect_sync_events(websocket)
            assert [event["event"] for event in sync_events] == [
                "welcome",
                "sync_start",
                "snapshot_chunk",
                "stats_update",
                "sync_complete",
            ]
            initial_prisoners = sync_events[2]["payload"]["prisoners"]
            assert [row["prisoner_id"] for row in initial_prisoners] == [seeded_prisoner_id]

            ingest_response = client.post(
                "/api/ingest",
                headers={"Authorization": "Bearer current-forwarder-key"},
                json={
                    "delivery_id": str(uuid4()),
                    "protocol": "ssh",
                    "timestamp": (anchor + timedelta(minutes=1)).isoformat(),
                    "credentials": ["root:toor"],
                    "commands": ["id"],
                    "downloads": [],
                },
            )
            assert ingest_response.status_code == 200
            assert ingest_response.json()["status"] == "processed"
            assert ingest_response.json()["outcome"] == "created"

            live_prisoner_event = websocket.receive_json()
            assert live_prisoner_event["event"] == "new_prisoner"

            asyncio.run(client.app.state.stats_broadcaster.publish_if_changed_once())
            live_stats_event = websocket.receive_json()
            assert live_stats_event["event"] == "stats_update"
            assert live_stats_event["payload"]["changed"] is True

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
            reconnect_prisoners = reconnect_events[2]["payload"]["prisoners"]
            reconnect_prisoner_ids = [row["prisoner_id"] for row in reconnect_prisoners]
            assert len(reconnect_prisoner_ids) == 2
            assert seeded_prisoner_id in reconnect_prisoner_ids
