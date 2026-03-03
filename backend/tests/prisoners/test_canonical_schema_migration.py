"""Canonical prisoner schema and migration behavior tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import UniqueConstraint, create_engine, text

from app.models.prisoner import Prisoner


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_model_contract_is_canonical_by_source_ip() -> None:
    table = Prisoner.__table__
    table_constraints = [constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)]
    unique_sets = {tuple(column.name for column in constraint.columns) for constraint in table_constraints}

    assert ("source_ip",) in unique_sets
    assert "protocol" not in table.c
    assert "attempt_count" in table.c
    assert "country_code" in table.c
    assert "first_seen_at" in table.c
    assert "last_seen_at" in table.c

    relationships = {relationship.key for relationship in Prisoner.__mapper__.relationships}
    assert relationships >= {
        "protocol_activities",
        "credentials",
        "commands",
        "downloads",
    }


def test_migration_merges_protocol_split_rows_deterministically(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'canonical-merge.sqlite3'}"
    alembic_config = _alembic_config(database_url)
    command.upgrade(alembic_config, "20260303_02")

    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO prisoners (
                    id, source_ip, protocol, first_seen_at, last_seen_at,
                    credential_count, command_count, download_count
                ) VALUES
                    (1, '203.0.113.10', 'ssh', :ssh_first, :ssh_last, 3, 2, 1),
                    (2, '203.0.113.10', 'telnet', :telnet_first, :telnet_last, 1, 4, 0),
                    (3, '198.51.100.20', 'ssh', :other_first, :other_last, 2, 1, 1)
                """
            ),
            {
                "ssh_first": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
                "ssh_last": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
                "telnet_first": datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc),
                "telnet_last": datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc),
                "other_first": datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc),
                "other_last": datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO ingest_deliveries (id, delivery_id, protocol, source_ip, prisoner_id, created_at)
                VALUES
                    (11, 'delivery-001', 'ssh', '203.0.113.10', 1, :created_at),
                    (12, 'delivery-002', 'telnet', '203.0.113.10', 2, :created_at)
                """
            ),
            {"created_at": datetime(2026, 1, 1, 13, 1, tzinfo=timezone.utc)},
        )

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        merged = connection.execute(
            text(
                """
                SELECT source_ip, attempt_count, first_seen_at, last_seen_at, credential_count, command_count, download_count
                FROM prisoners
                WHERE source_ip = '203.0.113.10'
                """
            )
        ).one()
        assert merged.source_ip == "203.0.113.10"
        assert merged.attempt_count == 11
        assert merged.first_seen_at == "2026-01-01 09:30:00.000000"
        assert merged.last_seen_at == "2026-01-01 13:00:00.000000"
        assert merged.credential_count == 4
        assert merged.command_count == 6
        assert merged.download_count == 1

        protocol_rows = connection.execute(
            text(
                """
                SELECT protocol, attempt_count, first_seen_at, last_seen_at
                FROM prisoner_protocol_activities
                JOIN prisoners ON prisoners.id = prisoner_protocol_activities.prisoner_id
                WHERE prisoners.source_ip = '203.0.113.10'
                ORDER BY protocol ASC
                """
            )
        ).all()
        assert protocol_rows == [
            ("ssh", 6, "2026-01-01 10:00:00.000000", "2026-01-01 12:00:00.000000"),
            ("telnet", 5, "2026-01-01 09:30:00.000000", "2026-01-01 13:00:00.000000"),
        ]

        delivery_links = connection.execute(
            text(
                """
                SELECT COUNT(DISTINCT prisoner_id)
                FROM ingest_deliveries
                WHERE source_ip = '203.0.113.10'
                """
            )
        ).scalar_one()
        assert delivery_links == 1
