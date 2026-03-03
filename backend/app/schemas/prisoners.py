"""Prisoner query response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PrisonerSummary(BaseModel):
    """Summary row for prisoner list responses."""

    model_config = ConfigDict(extra="forbid")

    id: int
    source_ip: str
    country_code: Optional[str]
    attempt_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    credential_count: int
    command_count: int
    download_count: int
    enrichment: "PrisonerEnrichmentSummary"


class PrisonerEnrichmentSummary(BaseModel):
    """Lightweight enrichment snapshot included in list rows."""

    model_config = ConfigDict(extra="forbid")

    status: str
    last_updated_at: Optional[datetime]
    country_code: Optional[str]
    asn: Optional[str]
    reputation_severity: Optional[str]


class PrisonerListResponse(BaseModel):
    """Cursor-paginated prisoner list response."""

    model_config = ConfigDict(extra="forbid")

    items: list[PrisonerSummary]
    next_cursor: Optional[str]


class PrisonerProtocolHistoryEntry(BaseModel):
    """Protocol-level persisted history for a prisoner."""

    model_config = ConfigDict(extra="forbid")

    protocol: str
    attempt_count: int
    first_seen_at: datetime
    last_seen_at: datetime


class PrisonerCredentialHistoryEntry(BaseModel):
    """Credential history record for a prisoner."""

    model_config = ConfigDict(extra="forbid")

    protocol: str
    credential: str
    observed_at: datetime


class PrisonerCommandHistoryEntry(BaseModel):
    """Command history record for a prisoner."""

    model_config = ConfigDict(extra="forbid")

    protocol: str
    command: str
    observed_at: datetime


class PrisonerDownloadHistoryEntry(BaseModel):
    """Download history record for a prisoner."""

    model_config = ConfigDict(extra="forbid")

    protocol: str
    download_url: str
    observed_at: datetime


class PrisonerEnrichmentGeo(BaseModel):
    """Normalized geo intel fields for prisoner detail responses."""

    model_config = ConfigDict(extra="forbid")

    country_code: Optional[str]
    asn: Optional[str]


class PrisonerEnrichmentReputation(BaseModel):
    """Normalized reputation intel fields for prisoner detail responses."""

    model_config = ConfigDict(extra="forbid")

    severity: Optional[str]
    confidence: Optional[int]


class PrisonerEnrichmentDetail(BaseModel):
    """Full enrichment payload included in prisoner detail responses."""

    model_config = ConfigDict(extra="forbid")

    status: str
    last_updated_at: Optional[datetime]
    provider: Optional[str]
    geo: PrisonerEnrichmentGeo
    reputation: PrisonerEnrichmentReputation
    reason_metadata: dict[str, str]


class PrisonerDetailPrisoner(PrisonerSummary):
    """Prisoner base fields plus full enrichment intel for detail responses."""

    model_config = ConfigDict(extra="forbid")

    enrichment: PrisonerEnrichmentDetail


class PrisonerDetailResponse(BaseModel):
    """Detail response with sectioned persisted histories."""

    model_config = ConfigDict(extra="forbid")

    prisoner: PrisonerDetailPrisoner
    protocol_history: list[PrisonerProtocolHistoryEntry]
    credentials: list[PrisonerCredentialHistoryEntry]
    commands: list[PrisonerCommandHistoryEntry]
    downloads: list[PrisonerDownloadHistoryEntry]
