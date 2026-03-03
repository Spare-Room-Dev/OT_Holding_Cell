"""Idempotency persistence record for ingest deliveries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IngestDelivery(Base):
    """Tracks each accepted delivery_id exactly once."""

    __tablename__ = "ingest_deliveries"
    __table_args__ = (UniqueConstraint("delivery_id", name="uq_ingest_delivery_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_id: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    source_ip: Mapped[str] = mapped_column(String(64), nullable=False)
    prisoner_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("prisoners.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    @classmethod
    def from_payload(cls, *, delivery_id: UUID, protocol: str, source_ip: str) -> "IngestDelivery":
        return cls(
            delivery_id=str(delivery_id),
            protocol=protocol,
            source_ip=source_ip,
        )
