"""Replay-safety tests for ingest delivery idempotency."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ingest_delivery import IngestDelivery


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_migration_enforces_unique_delivery_id(tmp_path: Path) -> None:
    database_path = tmp_path / "ingest-idempotency.sqlite3"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        session.add(
            IngestDelivery(
                delivery_id="delivery-001",
                source_ip="203.0.113.10",
                protocol="ssh",
            )
        )
        session.commit()

        session.add(
            IngestDelivery(
                delivery_id="delivery-001",
                source_ip="203.0.113.10",
                protocol="ssh",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
