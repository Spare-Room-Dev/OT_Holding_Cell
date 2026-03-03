"""Persistent lifetime rollups preserved across retention purges."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LifetimeRollup(Base):
    """Stores aggregate attempt totals for long-lived headline metrics."""

    __tablename__ = "lifetime_rollups"
    __table_args__ = (UniqueConstraint("rollup_key", name="uq_lifetime_rollup_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rollup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    country_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
