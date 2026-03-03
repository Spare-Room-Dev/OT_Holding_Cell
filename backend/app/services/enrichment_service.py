"""Provider adapters and lifecycle state machine for threat enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping

import httpx

from app.core.config import get_settings

COUNTRY_REASON_KEY = "country_code"
ASN_REASON_KEY = "asn"
REPUTATION_REASON_KEY = "reputation"

PROVIDER_SUCCESS_REASON = "provider_success"
MISSING_CREDENTIALS_REASON = "missing_credentials"
NO_DATA_REASON = "no_data"
PROVIDER_ERROR_REASON = "provider_error"
QUOTA_EXCEEDED_REASON = "quota_exceeded"
PROVIDER_TIMEOUT_REASON = "provider_timeout"
UNAUTHORIZED_REASON = "provider_unauthorized"
UNKNOWN_REASON = "unknown"

PENDING_REASONS = {"pending", "awaiting_enrichment"}

IPINFO_URL_TEMPLATE = "https://ipinfo.io/{ip}/json"
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"

_ASN_PATTERN = re.compile(r"\bAS\d+\b")


@dataclass(frozen=True)
class ExistingEnrichmentState:
    """Current prisoner enrichment state before a provider attempt."""

    status: str
    country_code: str | None
    asn: str | None
    reputation_severity: str | None
    reputation_confidence: int | None
    reason_metadata: Mapping[str, str]
    provider: str | None
    last_enriched_at: datetime | None


@dataclass(frozen=True)
class EnrichmentResult:
    """Canonical normalized enrichment payload."""

    status: str
    country_code: str | None
    asn: str | None
    reputation_severity: str | None
    reputation_confidence: int | None
    reason_metadata: dict[str, str]
    provider: str | None
    last_enriched_at: datetime | None
    quota_limited: bool


def _coerce_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def normalize_ipinfo_geo_payload(payload: Mapping[str, Any]) -> tuple[str | None, str | None, dict[str, str]]:
    """Normalize country + ASN fields from IPinfo payload."""

    country_code: str | None = None
    raw_country = payload.get("country")
    if isinstance(raw_country, str) and len(raw_country.strip()) == 2:
        country_code = raw_country.strip().upper()

    asn: str | None = None
    raw_asn = payload.get("asn")
    if isinstance(raw_asn, Mapping):
        raw_asn_value = raw_asn.get("asn")
        if isinstance(raw_asn_value, str):
            asn = raw_asn_value.strip().upper() or None

    if asn is None:
        org = payload.get("org")
        if isinstance(org, str):
            match = _ASN_PATTERN.search(org.upper())
            if match is not None:
                asn = match.group(0)

    return (
        country_code,
        asn,
        {
            COUNTRY_REASON_KEY: PROVIDER_SUCCESS_REASON if country_code else NO_DATA_REASON,
            ASN_REASON_KEY: PROVIDER_SUCCESS_REASON if asn else NO_DATA_REASON,
        },
    )


def _normalize_reputation_severity(confidence: int) -> str:
    if confidence == 0:
        return "none"
    if confidence < 40:
        return "low"
    if confidence < 70:
        return "medium"
    return "high"


def normalize_abuseipdb_reputation_payload(payload: Mapping[str, Any]) -> tuple[str | None, int | None, str]:
    """Normalize reputation severity + confidence fields from AbuseIPDB payload."""

    body: Mapping[str, Any]
    raw_data = payload.get("data")
    if isinstance(raw_data, Mapping):
        body = raw_data
    else:
        body = payload

    raw_confidence = body.get("abuseConfidenceScore")
    confidence: int | None = None

    if isinstance(raw_confidence, int):
        confidence = raw_confidence
    elif isinstance(raw_confidence, str) and raw_confidence.strip().isdigit():
        confidence = int(raw_confidence.strip())

    if confidence is None:
        return None, None, NO_DATA_REASON

    normalized_confidence = max(0, min(confidence, 100))
    return (
        _normalize_reputation_severity(normalized_confidence),
        normalized_confidence,
        PROVIDER_SUCCESS_REASON,
    )


def _is_pending_reason(reason: str | None) -> bool:
    if reason is None:
        return False
    return reason in PENDING_REASONS


def derive_enrichment_status(
    *,
    country_code: str | None,
    asn: str | None,
    reputation_severity: str | None,
    reputation_confidence: int | None,
    reason_metadata: Mapping[str, str],
    previous_status: str | None,
) -> str:
    """Derive locked lifecycle status from normalized enrichment payload."""

    geo_success = country_code is not None and asn is not None
    reputation_success = reputation_severity is not None and reputation_confidence is not None

    geo_pending = (
        country_code is None
        and asn is None
        and _is_pending_reason(reason_metadata.get(COUNTRY_REASON_KEY))
        and _is_pending_reason(reason_metadata.get(ASN_REASON_KEY))
    )
    reputation_pending = (
        reputation_severity is None
        and reputation_confidence is None
        and _is_pending_reason(reason_metadata.get(REPUTATION_REASON_KEY))
    )

    if geo_pending and reputation_pending:
        next_status = "pending"
    elif geo_success and reputation_success:
        next_status = "complete"
    elif geo_success or reputation_success:
        next_status = "partial"
    else:
        next_status = "failed"

    if previous_status == "complete" and next_status in {"partial", "failed"}:
        return "complete"

    return next_status


def _merge_provider_identities(previous_provider: str | None, attempt_provider: str | None) -> str | None:
    providers: list[str] = []

    for raw_value in (previous_provider, attempt_provider):
        if not raw_value:
            continue
        for provider_name in raw_value.split("+"):
            normalized = provider_name.strip()
            if normalized and normalized not in providers:
                providers.append(normalized)

    if not providers:
        return None

    return "+".join(providers)


def merge_enrichment_result(*, previous: ExistingEnrichmentState, attempt: EnrichmentResult) -> EnrichmentResult:
    """Merge a provider attempt with prior prisoner state, preserving successful intel."""

    country_code = attempt.country_code or previous.country_code
    asn = attempt.asn or previous.asn
    reputation_severity = attempt.reputation_severity or previous.reputation_severity
    reputation_confidence = attempt.reputation_confidence
    if reputation_confidence is None:
        reputation_confidence = previous.reputation_confidence

    merged_reason_metadata: dict[str, str] = {
        COUNTRY_REASON_KEY: PROVIDER_SUCCESS_REASON
        if country_code is not None
        else attempt.reason_metadata.get(COUNTRY_REASON_KEY)
        or previous.reason_metadata.get(COUNTRY_REASON_KEY)
        or UNKNOWN_REASON,
        ASN_REASON_KEY: PROVIDER_SUCCESS_REASON
        if asn is not None
        else attempt.reason_metadata.get(ASN_REASON_KEY)
        or previous.reason_metadata.get(ASN_REASON_KEY)
        or UNKNOWN_REASON,
        REPUTATION_REASON_KEY: PROVIDER_SUCCESS_REASON
        if reputation_severity is not None and reputation_confidence is not None
        else attempt.reason_metadata.get(REPUTATION_REASON_KEY)
        or previous.reason_metadata.get(REPUTATION_REASON_KEY)
        or UNKNOWN_REASON,
    }

    merged_last_enriched_at = attempt.last_enriched_at or previous.last_enriched_at
    merged_provider = _merge_provider_identities(previous.provider, attempt.provider)
    merged_status = derive_enrichment_status(
        country_code=country_code,
        asn=asn,
        reputation_severity=reputation_severity,
        reputation_confidence=reputation_confidence,
        reason_metadata=merged_reason_metadata,
        previous_status=previous.status,
    )

    return EnrichmentResult(
        status=merged_status,
        country_code=country_code,
        asn=asn,
        reputation_severity=reputation_severity,
        reputation_confidence=reputation_confidence,
        reason_metadata=merged_reason_metadata,
        provider=merged_provider,
        last_enriched_at=merged_last_enriched_at,
        quota_limited=attempt.quota_limited,
    )


def _request_provider_payload(
    *,
    client: httpx.Client,
    url: str,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, str] | None = None,
    timeout_seconds: int,
) -> tuple[Mapping[str, Any] | None, str, bool]:
    try:
        response = client.get(
            url,
            headers=headers,
            params=params,
            timeout=httpx.Timeout(timeout_seconds),
        )
    except httpx.TimeoutException:
        return None, PROVIDER_TIMEOUT_REASON, False
    except httpx.HTTPError:
        return None, PROVIDER_ERROR_REASON, False

    if response.status_code == 429:
        return None, QUOTA_EXCEEDED_REASON, True
    if response.status_code in {401, 403}:
        return None, UNAUTHORIZED_REASON, False
    if response.status_code >= 400:
        return None, PROVIDER_ERROR_REASON, False

    try:
        parsed = response.json()
    except ValueError:
        return None, PROVIDER_ERROR_REASON, False

    if not isinstance(parsed, Mapping):
        return None, PROVIDER_ERROR_REASON, False

    return parsed, PROVIDER_SUCCESS_REASON, False


def _extract_secret(value: Any) -> str | None:
    if value is None:
        return None

    raw_value = value.get_secret_value().strip()
    if not raw_value:
        return None

    return raw_value


def _fetch_geo_enrichment(
    *,
    client: httpx.Client,
    source_ip: str,
    timeout_seconds: int,
) -> tuple[str | None, str | None, dict[str, str], bool, bool]:
    settings = get_settings()
    ipinfo_token = _extract_secret(settings.ipinfo_token)
    if ipinfo_token is None:
        return (
            None,
            None,
            {
                COUNTRY_REASON_KEY: MISSING_CREDENTIALS_REASON,
                ASN_REASON_KEY: MISSING_CREDENTIALS_REASON,
            },
            False,
            False,
        )

    payload, reason, quota_limited = _request_provider_payload(
        client=client,
        url=IPINFO_URL_TEMPLATE.format(ip=source_ip),
        params={"token": ipinfo_token},
        timeout_seconds=timeout_seconds,
    )
    if payload is None:
        return (
            None,
            None,
            {
                COUNTRY_REASON_KEY: reason,
                ASN_REASON_KEY: reason,
            },
            False,
            quota_limited,
        )

    country_code, asn, reasons = normalize_ipinfo_geo_payload(payload)
    geo_success = country_code is not None and asn is not None
    return country_code, asn, reasons, geo_success, quota_limited


def _fetch_reputation_enrichment(
    *,
    client: httpx.Client,
    source_ip: str,
    timeout_seconds: int,
) -> tuple[str | None, int | None, str, bool, bool]:
    settings = get_settings()
    api_key = _extract_secret(settings.abuseipdb_api_key)
    if api_key is None:
        return None, None, MISSING_CREDENTIALS_REASON, False, False

    payload, reason, quota_limited = _request_provider_payload(
        client=client,
        url=ABUSEIPDB_URL,
        headers={
            "Accept": "application/json",
            "Key": api_key,
        },
        params={
            "ipAddress": source_ip,
            "maxAgeInDays": "90",
        },
        timeout_seconds=timeout_seconds,
    )
    if payload is None:
        return None, None, reason, False, quota_limited

    severity, confidence, reputation_reason = normalize_abuseipdb_reputation_payload(payload)
    success = severity is not None and confidence is not None
    return severity, confidence, reputation_reason, success, quota_limited


def enrich_ip_intel(
    *,
    source_ip: str,
    now: datetime | None = None,
    client: httpx.Client | None = None,
) -> EnrichmentResult:
    """Execute provider calls and return one canonical enrichment attempt result."""

    settings = get_settings()
    event_time = _coerce_utc(now or datetime.now(timezone.utc))

    owns_client = client is None
    http_client = client or httpx.Client()

    try:
        (
            country_code,
            asn,
            geo_reasons,
            geo_success,
            geo_quota_limited,
        ) = _fetch_geo_enrichment(
            client=http_client,
            source_ip=source_ip,
            timeout_seconds=settings.enrichment_provider_timeout_seconds,
        )
        (
            reputation_severity,
            reputation_confidence,
            reputation_reason,
            reputation_success,
            reputation_quota_limited,
        ) = _fetch_reputation_enrichment(
            client=http_client,
            source_ip=source_ip,
            timeout_seconds=settings.enrichment_provider_timeout_seconds,
        )
    finally:
        if owns_client:
            http_client.close()

    reason_metadata = {
        COUNTRY_REASON_KEY: geo_reasons[COUNTRY_REASON_KEY],
        ASN_REASON_KEY: geo_reasons[ASN_REASON_KEY],
        REPUTATION_REASON_KEY: reputation_reason,
    }

    provider_parts: list[str] = []
    if geo_success:
        provider_parts.append("ipinfo")
    if reputation_success:
        provider_parts.append("abuseipdb")

    status = derive_enrichment_status(
        country_code=country_code,
        asn=asn,
        reputation_severity=reputation_severity,
        reputation_confidence=reputation_confidence,
        reason_metadata=reason_metadata,
        previous_status=None,
    )

    return EnrichmentResult(
        status=status,
        country_code=country_code,
        asn=asn,
        reputation_severity=reputation_severity,
        reputation_confidence=reputation_confidence,
        reason_metadata=reason_metadata,
        provider="+".join(provider_parts) if provider_parts else None,
        last_enriched_at=event_time if provider_parts else None,
        quota_limited=geo_quota_limited or reputation_quota_limited,
    )
