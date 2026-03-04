"""Schema contracts for typed realtime stream envelopes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.realtime import (
    PrisonerEventPayload,
    RealtimeEventEnvelope,
    StatsUpdatePayload,
    SyncLifecyclePayload,
    WelcomePayload,
)


def _now_utc() -> datetime:
    return datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)


def _ordering(sequence: int = 1) -> dict[str, object]:
    return {
        "publish_sequence": sequence,
        "source_updated_at": _now_utc().isoformat(),
    }


def test_realtime_event_envelope_rejects_unknown_event_types() -> None:
    with pytest.raises(ValidationError):
        RealtimeEventEnvelope(
            event_id="evt-001",
            event="intrusion_detected",
            occurred_at=_now_utc(),
            protocol_version="v1",
            payload=WelcomePayload(
                ordering=_ordering(),
                server_time=_now_utc(),
            ).model_dump(mode="json"),
        )


def test_realtime_event_envelope_rejects_unknown_root_fields() -> None:
    payload = WelcomePayload(
        ordering=_ordering(),
        server_time=_now_utc(),
    )

    with pytest.raises(ValidationError):
        RealtimeEventEnvelope(
            event_id="evt-002",
            event="welcome",
            occurred_at=_now_utc(),
            protocol_version="v1",
            payload=payload.model_dump(mode="json"),
            unexpected_field=True,
        )


def test_prisoner_payload_requires_detail_sync_stale_hint() -> None:
    with pytest.raises(ValidationError):
        PrisonerEventPayload(
            ordering=_ordering(),
            prisoner_id=42,
            source_ip="198.51.100.20",
            country_code="US",
            attempt_count=12,
            first_seen_at=_now_utc(),
            last_seen_at=_now_utc(),
            credential_count=3,
            command_count=4,
            download_count=5,
            enrichment={
                "status": "partial",
                "last_updated_at": _now_utc().isoformat(),
                "country_code": "US",
                "asn": "AS64500",
                "reputation_severity": "medium",
            },
            detail_last_changed_at=_now_utc(),
        )


def test_prisoner_payload_rejects_embedded_detail_blob() -> None:
    with pytest.raises(ValidationError):
        PrisonerEventPayload(
            ordering=_ordering(),
            prisoner_id=42,
            source_ip="198.51.100.20",
            country_code="US",
            attempt_count=12,
            first_seen_at=_now_utc(),
            last_seen_at=_now_utc(),
            credential_count=3,
            command_count=4,
            download_count=5,
            enrichment={
                "status": "partial",
                "last_updated_at": _now_utc().isoformat(),
                "country_code": "US",
                "asn": "AS64500",
                "reputation_severity": "medium",
            },
            detail_sync_stale=True,
            detail_last_changed_at=_now_utc(),
            detail={"credentials": ["root:toor"]},
        )


def test_stats_payload_requires_ordering_metadata() -> None:
    with pytest.raises(ValidationError):
        StatsUpdatePayload(
            total_prisoners=10,
            active_prisoners=4,
            lifetime_attempts=99,
            lifetime_credentials=20,
            lifetime_commands=55,
            lifetime_downloads=10,
            changed=True,
        )


def test_occured_at_and_payload_timestamps_are_normalized_to_utc() -> None:
    local_offset = timezone(timedelta(hours=8))
    envelope = RealtimeEventEnvelope(
        event_id="evt-003",
        event="sync_start",
        occurred_at=datetime(2026, 3, 4, 20, 5, tzinfo=local_offset),
        protocol_version="v1",
        payload=SyncLifecyclePayload(
            ordering={
                "publish_sequence": 3,
                "source_updated_at": datetime(2026, 3, 4, 20, 4, tzinfo=local_offset),
            },
            sync_id="sync-01",
            estimated_total_chunks=2,
        ).model_dump(mode="json"),
    )

    assert envelope.occurred_at.tzinfo == timezone.utc
    assert envelope.payload.ordering.source_updated_at.tzinfo == timezone.utc
