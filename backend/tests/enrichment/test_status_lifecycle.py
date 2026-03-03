"""Status lifecycle and provider normalization contracts for enrichment service."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.enrichment_service import (
    EnrichmentResult,
    ExistingEnrichmentState,
    derive_enrichment_status,
    merge_enrichment_result,
    normalize_abuseipdb_reputation_payload,
    normalize_ipinfo_geo_payload,
)


def test_status_derivation_and_upgrade_paths_follow_locked_decisions() -> None:
    country_code, asn, geo_reasons = normalize_ipinfo_geo_payload(
        {
            "country": "us",
            "asn": {"asn": "AS13335"},
        }
    )
    severity, confidence, reputation_reason = normalize_abuseipdb_reputation_payload(
        {"data": {"abuseConfidenceScore": 92}}
    )

    assert (country_code, asn) == ("US", "AS13335")
    assert (severity, confidence) == ("high", 92)
    assert geo_reasons == {
        "country_code": "provider_success",
        "asn": "provider_success",
    }
    assert reputation_reason == "provider_success"

    failed_status = derive_enrichment_status(
        country_code=None,
        asn=None,
        reputation_severity=None,
        reputation_confidence=None,
        reason_metadata={
            "country_code": "provider_error",
            "asn": "provider_error",
            "reputation": "provider_error",
        },
        previous_status="pending",
    )
    assert failed_status == "failed"

    partial_status = derive_enrichment_status(
        country_code="US",
        asn="AS13335",
        reputation_severity=None,
        reputation_confidence=None,
        reason_metadata={
            "country_code": "provider_success",
            "asn": "provider_success",
            "reputation": "provider_error",
        },
        previous_status="failed",
    )
    assert partial_status == "partial"

    previous = ExistingEnrichmentState(
        status="failed",
        country_code=None,
        asn=None,
        reputation_severity=None,
        reputation_confidence=None,
        reason_metadata={
            "country_code": "provider_error",
            "asn": "provider_error",
            "reputation": "provider_error",
        },
        provider=None,
        last_enriched_at=None,
    )
    attempt = EnrichmentResult(
        status="complete",
        country_code="US",
        asn="AS13335",
        reputation_severity="high",
        reputation_confidence=92,
        reason_metadata={
            "country_code": "provider_success",
            "asn": "provider_success",
            "reputation": "provider_success",
        },
        provider="ipinfo+abuseipdb",
        last_enriched_at=datetime(2026, 3, 3, 14, 0, tzinfo=timezone.utc),
        quota_limited=False,
    )

    upgraded = merge_enrichment_result(previous=previous, attempt=attempt)

    assert upgraded.status == "complete"
    assert upgraded.country_code == "US"
    assert upgraded.asn == "AS13335"
    assert upgraded.reputation_severity == "high"
    assert upgraded.reputation_confidence == 92
    assert upgraded.provider == "ipinfo+abuseipdb"
    assert upgraded.reason_metadata == {
        "country_code": "provider_success",
        "asn": "provider_success",
        "reputation": "provider_success",
    }
    assert upgraded.last_enriched_at == datetime(2026, 3, 3, 14, 0, tzinfo=timezone.utc)
