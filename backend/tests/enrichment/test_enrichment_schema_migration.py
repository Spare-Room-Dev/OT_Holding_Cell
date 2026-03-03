"""Schema and ORM contracts for async threat enrichment foundation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import UniqueConstraint, create_engine, inspect, text
from sqlalchemy import UniqueConstraint

from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_enrichment_model_defaults_pending_and_null_intel_fields() -> None:
    prisoner_table = Prisoner.__table__
    expected_columns = {
        "enrichment_status",
        "enrichment_country_code",
        "enrichment_asn",
        "enrichment_reputation_severity",
        "enrichment_reputation_confidence",
        "enrichment_reason_metadata",
        "enrichment_provider",
        "last_enriched_at",
    }
    assert expected_columns.issubset(set(prisoner_table.c.keys()))
    assert prisoner_table.c.enrichment_status.nullable is False
    assert prisoner_table.c.enrichment_status.default is not None
    assert prisoner_table.c.enrichment_status.default.arg == "pending"
    assert prisoner_table.c.enrichment_country_code.nullable is True
    assert prisoner_table.c.enrichment_asn.nullable is True
    assert prisoner_table.c.enrichment_reputation_severity.nullable is True
    assert prisoner_table.c.enrichment_reputation_confidence.nullable is True
    assert prisoner_table.c.last_enriched_at.nullable is True

    relationships = {relationship.key for relationship in Prisoner.__mapper__.relationships}
    assert "enrichment_jobs" in relationships

    job_table = EnrichmentJob.__table__
    expected_job_columns = {
        "id",
        "prisoner_id",
        "status",
        "attempt_count",
        "max_attempts",
        "available_at",
        "claimed_at",
        "completed_at",
        "failure_reason_metadata",
        "created_at",
    }
    assert expected_job_columns.issubset(set(job_table.c.keys()))
    assert job_table.c.status.default is not None
    assert job_table.c.status.default.arg == "queued"
    assert job_table.c.attempt_count.default is not None
    assert job_table.c.attempt_count.default.arg == 0
    assert job_table.c.max_attempts.default is not None
    assert job_table.c.max_attempts.default.arg >= 1
    assert job_table.c.failure_reason_metadata.nullable is False
    assert job_table.c.failure_reason_metadata.default is not None

    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in job_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("prisoner_id", "status") not in unique_constraints


def test_async_enrichment_migration_adds_queue_and_status_columns(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'async-enrichment.sqlite3'}"
    alembic_config = _alembic_config(database_url)
    command.upgrade(alembic_config, "20260303_04")

    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO prisoners (
                    source_ip, country_code, attempt_count, first_seen_at, last_seen_at,
                    credential_count, command_count, download_count
                ) VALUES (
                    '203.0.113.90', 'US', 3, :first_seen_at, :last_seen_at, 1, 1, 1
                )
                """
            ),
            {
                "first_seen_at": datetime(2026, 3, 3, 8, 0, tzinfo=timezone.utc),
                "last_seen_at": datetime(2026, 3, 3, 8, 5, tzinfo=timezone.utc),
            },
        )

    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")

    schema = inspect(engine)
    prisoner_columns = {column["name"] for column in schema.get_columns("prisoners")}
    assert {
        "enrichment_status",
        "enrichment_country_code",
        "enrichment_asn",
        "enrichment_reputation_severity",
        "enrichment_reputation_confidence",
        "enrichment_reason_metadata",
        "enrichment_provider",
        "last_enriched_at",
    }.issubset(prisoner_columns)

    queue_columns = {column["name"] for column in schema.get_columns("enrichment_jobs")}
    assert {
        "id",
        "prisoner_id",
        "status",
        "attempt_count",
        "max_attempts",
        "available_at",
        "claimed_at",
        "completed_at",
        "failure_reason_metadata",
        "created_at",
    }.issubset(queue_columns)

    queue_indexes = {index["name"] for index in schema.get_indexes("enrichment_jobs")}
    assert "ix_enrichment_jobs_claim_fifo" in queue_indexes

    foreign_keys = schema.get_foreign_keys("enrichment_jobs")
    assert any(
        foreign_key["referred_table"] == "prisoners"
        and foreign_key["constrained_columns"] == ["prisoner_id"]
        for foreign_key in foreign_keys
    )

    with engine.connect() as connection:
        existing_prisoner = connection.execute(
            text(
                """
                SELECT enrichment_status, enrichment_reason_metadata
                FROM prisoners
                WHERE source_ip = '203.0.113.90'
                """
            )
        ).one()
        assert existing_prisoner.enrichment_status == "pending"
        assert existing_prisoner.enrichment_reason_metadata is not None
