"""Create persistent forwarder_heartbeats table for liveness checks."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_02"
down_revision = "20260303_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forwarder_heartbeats",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_ip", "protocol", name="uq_forwarder_heartbeat_identity"),
    )


def downgrade() -> None:
    op.drop_table("forwarder_heartbeats")
