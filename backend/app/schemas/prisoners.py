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


class PrisonerListResponse(BaseModel):
    """Cursor-paginated prisoner list response."""

    model_config = ConfigDict(extra="forbid")

    items: list[PrisonerSummary]
    next_cursor: Optional[str]
