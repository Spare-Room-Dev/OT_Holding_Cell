"""Retention execution metadata for operator verification."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RetentionRun(Base):
    """Tracks each retention attempt and purge outcomes."""

    __tablename__ = "retention_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prisoner_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_prisoner_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deleted_delivery_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
