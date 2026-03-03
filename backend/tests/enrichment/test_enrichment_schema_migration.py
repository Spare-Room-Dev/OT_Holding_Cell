"""Schema and ORM contracts for async threat enrichment foundation."""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner


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
