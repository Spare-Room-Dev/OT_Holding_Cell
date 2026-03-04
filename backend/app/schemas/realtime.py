"""Typed schema contracts for realtime websocket stream events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.prisoners import PrisonerEnrichmentSummary

RealtimeEventName = Literal[
    "welcome",
    "sync_start",
    "snapshot_chunk",
    "sync_complete",
    "new_prisoner",
    "prisoner_updated",
    "prisoner_enriched",
    "stats_update",
]


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return value.astimezone(timezone.utc)


class RealtimeOrderingMetadata(BaseModel):
    """Ordering metadata used by clients for newest-wins reconciliation."""

    model_config = ConfigDict(extra="forbid")

    publish_sequence: int
    source_updated_at: datetime

    @field_validator("publish_sequence")
    @classmethod
    def validate_publish_sequence(cls, value: int) -> int:
        if value < 1:
            raise ValueError("publish_sequence must be greater than zero")
        return value

    @field_validator("source_updated_at")
    @classmethod
    def validate_source_updated_at(cls, value: datetime) -> datetime:
        return _normalize_utc(value)


class WelcomePayload(BaseModel):
    """Handshake payload sent immediately after websocket connect."""

    model_config = ConfigDict(extra="forbid")

    ordering: RealtimeOrderingMetadata
    server_time: datetime

    @field_validator("server_time")
    @classmethod
    def validate_server_time(cls, value: datetime) -> datetime:
        return _normalize_utc(value)


class SyncLifecyclePayload(BaseModel):
    """Payload for sync lifecycle events (`sync_start` and `sync_complete`)."""

    model_config = ConfigDict(extra="forbid")

    ordering: RealtimeOrderingMetadata
    sync_id: str
    estimated_total_chunks: int

    @field_validator("estimated_total_chunks")
    @classmethod
    def validate_estimated_total_chunks(cls, value: int) -> int:
        if value < 0:
            raise ValueError("estimated_total_chunks cannot be negative")
        return value


class PrisonerEventPayload(BaseModel):
    """Realtime prisoner summary payload including detail-stale hint fields."""

    model_config = ConfigDict(extra="forbid")

    ordering: RealtimeOrderingMetadata
    prisoner_id: int
    source_ip: str
    country_code: Optional[str]
    attempt_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    credential_count: int
    command_count: int
    download_count: int
    enrichment: PrisonerEnrichmentSummary
    detail_sync_stale: bool
    detail_last_changed_at: datetime

    @field_validator("attempt_count", "credential_count", "command_count", "download_count")
    @classmethod
    def validate_non_negative_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("count fields cannot be negative")
        return value

    @field_validator("first_seen_at", "last_seen_at", "detail_last_changed_at")
    @classmethod
    def validate_datetime_fields(cls, value: datetime) -> datetime:
        return _normalize_utc(value)


class SnapshotChunkPayload(BaseModel):
    """Payload for chunked snapshot hydration during reconnect sync."""

    model_config = ConfigDict(extra="forbid")

    ordering: RealtimeOrderingMetadata
    sync_id: str
    chunk_index: int
    total_chunks: int
    prisoners: list[PrisonerEventPayload]

    @field_validator("chunk_index", "total_chunks")
    @classmethod
    def validate_chunk_sizes(cls, value: int) -> int:
        if value < 1:
            raise ValueError("chunk fields must be greater than zero")
        return value


class StatsUpdatePayload(BaseModel):
    """Payload for batched aggregate counters shown on the dashboard."""

    model_config = ConfigDict(extra="forbid")

    ordering: RealtimeOrderingMetadata
    total_prisoners: int
    active_prisoners: int
    lifetime_attempts: int
    lifetime_credentials: int
    lifetime_commands: int
    lifetime_downloads: int
    changed: bool

    @field_validator(
        "total_prisoners",
        "active_prisoners",
        "lifetime_attempts",
        "lifetime_credentials",
        "lifetime_commands",
        "lifetime_downloads",
    )
    @classmethod
    def validate_non_negative_totals(cls, value: int) -> int:
        if value < 0:
            raise ValueError("stats counters cannot be negative")
        return value


RealtimePayload = Union[
    WelcomePayload,
    SyncLifecyclePayload,
    SnapshotChunkPayload,
    PrisonerEventPayload,
    StatsUpdatePayload,
]

_PAYLOAD_BY_EVENT: dict[str, type[BaseModel]] = {
    "welcome": WelcomePayload,
    "sync_start": SyncLifecyclePayload,
    "snapshot_chunk": SnapshotChunkPayload,
    "sync_complete": SyncLifecyclePayload,
    "new_prisoner": PrisonerEventPayload,
    "prisoner_updated": PrisonerEventPayload,
    "prisoner_enriched": PrisonerEventPayload,
    "stats_update": StatsUpdatePayload,
}


class RealtimeEventEnvelope(BaseModel):
    """Strict envelope contract for all outbound realtime websocket messages."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event: RealtimeEventName
    occurred_at: datetime
    protocol_version: str
    payload: RealtimePayload

    @model_validator(mode="before")
    @classmethod
    def validate_payload_matches_event(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        event = data.get("event")
        payload = data.get("payload")
        model_cls = _PAYLOAD_BY_EVENT.get(str(event))
        if model_cls is None:
            return data

        data["payload"] = model_cls.model_validate(payload)
        return data

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        return _normalize_utc(value)
