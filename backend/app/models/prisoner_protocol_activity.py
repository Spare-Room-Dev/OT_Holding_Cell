"""Per-protocol prisoner behavior history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.prisoner import Prisoner


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PrisonerProtocolActivity(Base):
    """Protocol-level first/last seen and attempt activity for a prisoner."""

    __tablename__ = "prisoner_protocol_activities"
    __table_args__ = (UniqueConstraint("prisoner_id", "protocol", name="uq_prisoner_protocol_activity_identity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prisoner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prisoners.id", ondelete="CASCADE"),
        nullable=False,
    )
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    prisoner: Mapped["Prisoner"] = relationship("Prisoner", back_populates="protocol_activities")
