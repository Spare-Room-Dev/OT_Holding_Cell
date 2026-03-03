"""Heartbeat liveness persistence and stale-window behavior tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _trusted_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer current-forwarder-key",
        "X-Forwarded-For": "203.0.113.10",
    }


def _heartbeat_payload(*, offset_seconds: int = 0) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return {
        "protocol": "ssh",
        "timestamp": timestamp.isoformat(),
    }


def _build_client(*, database_url: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", "current-forwarder-key")
    monkeypatch.setenv("INGEST_API_KEY_PREVIOUS", "previous-forwarder-key")
    monkeypatch.setenv("ALLOWED_FORWARDER_IPS", "[\"203.0.113.10\", \"127.0.0.1\"]")
    monkeypatch.setenv("INGEST_RATE_LIMIT_MAX_REQUESTS", "20")
    monkeypatch.setenv("INGEST_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("HEARTBEAT_RATE_LIMIT_MAX_REQUESTS", "20")
    monkeypatch.setenv("HEARTBEAT_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("HEARTBEAT_STALE_WARNING_SECONDS", "60")

    from app.core.config import get_settings
    from app.db.session import create_session_factory
    from app.main import create_app
    import app.db.session as db_session_module

    get_settings.cache_clear()
    db_session_module.SessionFactory = create_session_factory(database_url)
    return TestClient(create_app())


def test_migration_creates_forwarder_heartbeat_table(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'heartbeat-liveness.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    schema = inspect(create_engine(database_url, future=True))
    columns = {column["name"] for column in schema.get_columns("forwarder_heartbeats")}
    assert columns == {
        "id",
        "source_ip",
        "protocol",
        "last_seen_at",
        "created_at",
        "updated_at",
    }


def test_heartbeat_persists_liveness_state_and_returns_fresh_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'heartbeat-api.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    with _build_client(database_url=database_url, monkeypatch=monkeypatch) as client:
        response = client.post(
            "/api/heartbeat",
            headers=_trusted_headers(),
            json=_heartbeat_payload(),
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["is_stale"] is False
    assert response.json()["source_ip"] == "203.0.113.10"
    assert response.json()["protocol"] == "ssh"
    assert response.json()["stale_after_seconds"] == 60

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        rows = session.execute(
            text("SELECT source_ip, protocol FROM forwarder_heartbeats"),
        ).all()

    assert rows == [("203.0.113.10", "ssh")]


def test_heartbeat_marks_forwarder_stale_when_warning_window_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'heartbeat-stale.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    with _build_client(database_url=database_url, monkeypatch=monkeypatch) as client:
        response = client.post(
            "/api/heartbeat",
            headers=_trusted_headers(),
            json=_heartbeat_payload(offset_seconds=-120),
        )

    assert response.status_code == 200
    assert response.json()["is_stale"] is True
    assert response.json()["stale_after_seconds"] == 60


def test_liveness_state_is_persistent_across_app_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'heartbeat-restart.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    with _build_client(database_url=database_url, monkeypatch=monkeypatch) as client:
        first = client.post("/api/heartbeat", headers=_trusted_headers(), json=_heartbeat_payload(offset_seconds=-5))
    with _build_client(database_url=database_url, monkeypatch=monkeypatch) as client:
        second = client.post("/api/heartbeat", headers=_trusted_headers(), json=_heartbeat_payload())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["last_seen_at"] != second.json()["last_seen_at"]

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        count = session.execute(
            text("SELECT COUNT(*) FROM forwarder_heartbeats WHERE source_ip = :source_ip AND protocol = :protocol"),
            {"source_ip": "203.0.113.10", "protocol": "ssh"},
        ).scalar_one()

    assert count == 1
