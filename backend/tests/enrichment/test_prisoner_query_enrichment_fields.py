"""Enrichment visibility contracts for prisoner list/detail query surfaces."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import app.db.session as db_session_module
from app.models.prisoner import Prisoner


def _api_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _create_prisoner(*, source_ip: str, timestamp: datetime, enrichment_reasons: dict[str, str]) -> int:
    with db_session_module.SessionFactory() as session:
        prisoner = Prisoner(
            source_ip=source_ip,
            country_code=None,
            attempt_count=1,
            first_seen_at=timestamp,
            last_seen_at=timestamp,
            credential_count=0,
            command_count=0,
            download_count=0,
            enrichment_status="pending",
            enrichment_reason_metadata=enrichment_reasons,
        )
        session.add(prisoner)
        session.flush()
        session.commit()
        return prisoner.id


def _mark_prisoner_enriched(*, prisoner_id: int, enriched_at: datetime) -> None:
    with db_session_module.SessionFactory() as session:
        prisoner = session.get(Prisoner, prisoner_id)
        assert prisoner is not None
        prisoner.enrichment_status = "complete"
        prisoner.enrichment_country_code = "US"
        prisoner.enrichment_asn = "AS13335"
        prisoner.enrichment_reputation_severity = "high"
        prisoner.enrichment_reputation_confidence = 92
        prisoner.enrichment_provider = "ipinfo+abuseipdb"
        prisoner.last_enriched_at = enriched_at
        prisoner.enrichment_reason_metadata = {
            "geo": "provider_success",
            "reputation": "provider_success",
        }
        session.commit()


def test_prisoner_list_and_detail_include_enrichment_status_contract(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    prisoner_id = _create_prisoner(
        source_ip="198.51.100.101",
        timestamp=now - timedelta(minutes=10),
        enrichment_reasons={
            "geo": "awaiting_enrichment",
            "reputation": "awaiting_enrichment",
        },
    )

    list_response = client.get("/api/prisoners", params={"limit": 10})
    assert list_response.status_code == 200
    list_payload = list_response.json()
    list_item = next(row for row in list_payload["items"] if row["id"] == prisoner_id)
    assert list_item["enrichment"] == {
        "status": "pending",
        "last_updated_at": None,
        "country_code": None,
        "asn": None,
        "reputation_severity": None,
    }
    assert "reason_metadata" not in list_item["enrichment"]
    assert "provider" not in list_item["enrichment"]
    assert "reputation_confidence" not in list_item["enrichment"]

    pending_detail = client.get(f"/api/prisoners/{prisoner_id}")
    assert pending_detail.status_code == 200
    pending_payload = pending_detail.json()
    assert pending_payload["prisoner"]["enrichment"] == {
        "status": "pending",
        "last_updated_at": None,
        "provider": None,
        "geo": {"country_code": None, "asn": None},
        "reputation": {"severity": None, "confidence": None},
        "reason_metadata": {
            "geo": "awaiting_enrichment",
            "reputation": "awaiting_enrichment",
        },
    }

    enriched_at = now - timedelta(minutes=1)
    _mark_prisoner_enriched(prisoner_id=prisoner_id, enriched_at=enriched_at)

    refreshed_list = client.get("/api/prisoners", params={"limit": 10})
    assert refreshed_list.status_code == 200
    refreshed_item = next(row for row in refreshed_list.json()["items"] if row["id"] == prisoner_id)
    assert refreshed_item["enrichment"] == {
        "status": "complete",
        "last_updated_at": _api_timestamp(enriched_at),
        "country_code": "US",
        "asn": "AS13335",
        "reputation_severity": "high",
    }

    refreshed_detail = client.get(f"/api/prisoners/{prisoner_id}")
    assert refreshed_detail.status_code == 200
    refreshed_payload = refreshed_detail.json()
    assert refreshed_payload["prisoner"]["enrichment"] == {
        "status": "complete",
        "last_updated_at": _api_timestamp(enriched_at),
        "provider": "ipinfo+abuseipdb",
        "geo": {"country_code": "US", "asn": "AS13335"},
        "reputation": {"severity": "high", "confidence": 92},
        "reason_metadata": {
            "geo": "provider_success",
            "reputation": "provider_success",
        },
    }
