"""Strict heartbeat payload schema with bounded fields."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.ingest import _validate_timestamp_freshness

ProtocolType = Literal["ssh", "telnet"]


class HeartbeatPayload(BaseModel):
    """Validated payload contract for forwarder heartbeat traffic."""

    model_config = ConfigDict(extra="forbid")

    protocol: ProtocolType
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        return _validate_timestamp_freshness(value)
