"""Durable queue row for asynchronous threat enrichment retries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.prisoner import Prisoner


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EnrichmentJob(Base):
    """Persisted enrichment lifecycle state for deferred processing."""

    __tablename__ = "enrichment_jobs"
    __table_args__ = (
        Index(
            "ix_enrichment_jobs_claim_fifo",
            "status",
            "available_at",
            "created_at",
            "id",
        ),
        Index("ix_enrichment_jobs_prisoner_created", "prisoner_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prisoner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prisoners.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason_metadata: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    prisoner: Mapped["Prisoner"] = relationship("Prisoner", back_populates="enrichment_jobs")
