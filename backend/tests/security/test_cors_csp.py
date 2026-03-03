"""Origin allowlist coverage for API CORS, socket policy, and frontend CSP."""

from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest


APPROVED_ORIGIN = "https://app.holdingcell.test"
BLOCKED_ORIGIN = "https://evil.example"
APPROVED_API_TARGET = "https://api.holdingcell.test"
APPROVED_WSS_TARGET = "wss://api.holdingcell.test"


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def security_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_path = tmp_path / "security-cors.sqlite3"
    database_url = f"sqlite:///{database_path}"
    command.upgrade(_alembic_config(database_url), "head")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", "current-forwarder-key")
    monkeypatch.setenv("INGEST_API_KEY_PREVIOUS", "previous-forwarder-key")
    monkeypatch.setenv("ALLOWED_FORWARDER_IPS", "[\"203.0.113.10\", \"127.0.0.1\"]")
    monkeypatch.setenv("APPROVED_BROWSER_ORIGINS", f"[\"{APPROVED_ORIGIN}\"]")
    monkeypatch.setenv(
        "APPROVED_BACKEND_CONNECT_SRC",
        f"[\"{APPROVED_API_TARGET}\", \"{APPROVED_WSS_TARGET}\"]",
    )

    from app.core.config import get_settings
    from app.db.session import create_session_factory
    from app.main import create_app
    import app.db.session as db_session_module

    get_settings.cache_clear()
    db_session_module.SessionFactory = create_session_factory(database_url)
    return TestClient(create_app())


def test_cors_and_socket_allowlist_enforced(security_client: TestClient) -> None:
    allowed_preflight = security_client.options(
        "/api/ingest",
        headers={
            "Origin": APPROVED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    blocked_preflight = security_client.options(
        "/api/ingest",
        headers={
            "Origin": BLOCKED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )

    assert allowed_preflight.status_code == 200
    assert allowed_preflight.headers["access-control-allow-origin"] == APPROVED_ORIGIN
    assert blocked_preflight.status_code == 400
    assert blocked_preflight.headers.get("access-control-allow-origin") is None

    from app.core.config import get_settings
    from app.realtime.socket_server import is_socket_origin_allowed

    settings = get_settings()
    assert is_socket_origin_allowed(APPROVED_ORIGIN, settings) is True
    assert is_socket_origin_allowed(BLOCKED_ORIGIN, settings) is False


def test_frontend_csp_connect_src_is_restricted() -> None:
    frontend_root = Path(__file__).resolve().parents[3] / "frontend"
    vercel_json = frontend_root / "vercel.json"
    payload = json.loads(vercel_json.read_text(encoding="utf-8"))

    csp_values: list[str] = []
    for header_block in payload.get("headers", []):
        for header in header_block.get("headers", []):
            if header.get("key", "").lower() == "content-security-policy":
                csp_values.append(header.get("value", ""))

    assert csp_values, "Content-Security-Policy header must be defined in frontend/vercel.json"
    csp_value = csp_values[0]

    assert "connect-src" in csp_value
    assert APPROVED_API_TARGET in csp_value
    assert APPROVED_WSS_TARGET in csp_value
    assert "connect-src *" not in csp_value
