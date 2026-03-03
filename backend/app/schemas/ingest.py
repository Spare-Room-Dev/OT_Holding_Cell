"""Strict ingest payload schema with bounded fields."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TimestampFreshnessWindow = timedelta(minutes=15)
ProtocolType = Literal["ssh", "telnet"]

CredentialEntry = Annotated[str, Field(min_length=1, max_length=256)]
CommandEntry = Annotated[str, Field(min_length=1, max_length=2048)]
DownloadEntry = Annotated[str, Field(min_length=1, max_length=2048)]


def _validate_timestamp_freshness(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must include timezone")

    normalized = value.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    age_seconds = abs((now - normalized).total_seconds())
    if age_seconds > TimestampFreshnessWindow.total_seconds():
        raise ValueError("timestamp outside freshness window")

    return normalized


class IngestPayload(BaseModel):
    """Validated payload contract for untrusted ingest traffic."""

    model_config = ConfigDict(extra="forbid")

    delivery_id: UUID
    protocol: ProtocolType
    timestamp: datetime
    credentials: list[CredentialEntry] = Field(default_factory=list, max_length=100)
    commands: list[CommandEntry] = Field(default_factory=list, max_length=200)
    downloads: list[DownloadEntry] = Field(default_factory=list, max_length=100)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return _validate_timestamp_freshness(value)
