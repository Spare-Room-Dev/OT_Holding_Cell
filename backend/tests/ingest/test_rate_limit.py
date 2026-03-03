"""Rate-limit behavior tests for trusted ingest boundary endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


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


def _valid_ingest_payload() -> dict[str, object]:
    return {
        "delivery_id": str(uuid4()),
        "protocol": "ssh",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "credentials": ["root:toor"],
        "commands": ["whoami"],
        "downloads": ["http://example.invalid/dropper.bin"],
    }


def _valid_heartbeat_payload() -> dict[str, str]:
    return {
        "protocol": "ssh",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def rate_limit_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_path = tmp_path / "rate-limit.sqlite3"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(_alembic_config(database_url), "head")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", "current-forwarder-key")
    monkeypatch.setenv("INGEST_API_KEY_PREVIOUS", "previous-forwarder-key")
    monkeypatch.setenv("ALLOWED_FORWARDER_IPS", "[\"203.0.113.10\", \"127.0.0.1\"]")
    monkeypatch.setenv("INGEST_RATE_LIMIT_MAX_REQUESTS", "2")
    monkeypatch.setenv("INGEST_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("HEARTBEAT_RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("HEARTBEAT_RATE_LIMIT_WINDOW_SECONDS", "60")

    from app.core.config import get_settings
    from app.db.session import create_session_factory
    from app.main import create_app
    import app.db.session as db_session_module

    get_settings.cache_clear()
    db_session_module.SessionFactory = create_session_factory(database_url)
    return TestClient(create_app())


def test_ingest_returns_429_with_retry_contract(rate_limit_client: TestClient) -> None:
    response_1 = rate_limit_client.post("/api/ingest", headers=_trusted_headers(), json=_valid_ingest_payload())
    response_2 = rate_limit_client.post("/api/ingest", headers=_trusted_headers(), json=_valid_ingest_payload())
    response_3 = rate_limit_client.post("/api/ingest", headers=_trusted_headers(), json=_valid_ingest_payload())

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_3.status_code == 429

    retry_after = int(response_3.headers["Retry-After"])
    assert 1 <= retry_after <= 60
    assert response_3.headers["X-RateLimit-Limit"] == "2"
    assert response_3.headers["X-RateLimit-Remaining"] == "0"
    assert response_3.headers["X-RateLimit-Reset"].isdigit()

    assert response_3.json() == {
        "error": "rate_limit_exceeded",
        "message": "Too many requests for this endpoint. Retry after the specified delay.",
        "retry_after_seconds": retry_after,
    }


def test_heartbeat_uses_its_own_limit_policy(rate_limit_client: TestClient) -> None:
    heartbeat_1 = rate_limit_client.post(
        "/api/heartbeat",
        headers=_trusted_headers(),
        json=_valid_heartbeat_payload(),
    )
    heartbeat_2 = rate_limit_client.post(
        "/api/heartbeat",
        headers=_trusted_headers(),
        json=_valid_heartbeat_payload(),
    )

    assert heartbeat_1.status_code == 200
    assert heartbeat_2.status_code == 429
    assert heartbeat_2.headers["X-RateLimit-Limit"] == "1"
    assert heartbeat_2.json()["error"] == "rate_limit_exceeded"

    ingest_after_heartbeat_limit = rate_limit_client.post(
        "/api/ingest",
        headers=_trusted_headers(),
        json=_valid_ingest_payload(),
    )
    assert ingest_after_heartbeat_limit.status_code == 200
