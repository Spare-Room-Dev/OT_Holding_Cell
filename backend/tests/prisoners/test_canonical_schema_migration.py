"""Canonical prisoner schema and migration behavior tests."""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from app.models.prisoner import Prisoner


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
