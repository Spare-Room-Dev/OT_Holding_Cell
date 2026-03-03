"""Replay-safety tests for ingest delivery idempotency."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
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


def test_migration_creates_ingest_delivery_metadata_columns(tmp_path: Path) -> None:
    database_path = tmp_path / "ingest-idempotency.sqlite3"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    schema = inspect(engine)

    columns = {column["name"] for column in schema.get_columns("ingest_deliveries")}
    assert columns == {
        "id",
        "delivery_id",
        "protocol",
        "source_ip",
        "prisoner_id",
        "created_at",
    }

    unique_constraints = schema.get_unique_constraints("ingest_deliveries")
    assert any(
        constraint["name"] == "uq_ingest_delivery_id" and constraint["column_names"] == ["delivery_id"]
        for constraint in unique_constraints
    )

    foreign_keys = schema.get_foreign_keys("ingest_deliveries")
    assert any(
        foreign_key["referred_table"] == "prisoners"
        and foreign_key["constrained_columns"] == ["prisoner_id"]
        and foreign_key["referred_columns"] == ["id"]
        for foreign_key in foreign_keys
    )
