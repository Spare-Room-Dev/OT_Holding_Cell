"""Create prisoners and ingest_deliveries tables for replay-safe ingest."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prisoners",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("credential_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("command_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("source_ip", "protocol", name="uq_prisoner_identity"),
    )

    op.create_table(
        "ingest_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("delivery_id", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("delivery_id", name="uq_ingest_delivery_id"),
    )


def downgrade() -> None:
    op.drop_table("ingest_deliveries")
    op.drop_table("prisoners")
