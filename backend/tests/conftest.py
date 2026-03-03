"""Test fixtures for backend boundary tests."""

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from fastapi.testclient import TestClient


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    database_path = tmp_path / "boundary-tests.sqlite3"
    database_url = f"sqlite:///{database_path}"
    command.upgrade(_alembic_config(database_url), "head")

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

    from app.db.session import create_session_factory
    import app.db.session as db_session_module
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    db_session_module.SessionFactory = create_session_factory(database_url)
    app = create_app()
    return TestClient(app)
