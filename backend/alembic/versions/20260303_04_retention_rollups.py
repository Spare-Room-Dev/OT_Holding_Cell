"""Add lifetime rollups and retention run metadata tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_04"
down_revision = "20260303_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lifetime_rollups",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("rollup_key", sa.String(length=64), nullable=False),
        sa.Column("country_code", sa.String(length=16), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rollup_key", name="uq_lifetime_rollup_key"),
    )

    op.create_table(
        "retention_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prisoner_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_prisoner_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_delivery_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("retention_runs")
    op.drop_table("lifetime_rollups")
