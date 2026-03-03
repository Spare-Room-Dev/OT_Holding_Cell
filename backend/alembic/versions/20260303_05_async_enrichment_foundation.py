"""Add async enrichment prisoner fields and durable enrichment queue."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_05"
down_revision = "20260303_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prisoners",
        sa.Column("enrichment_status", sa.String(length=16), nullable=False, server_default="pending"),
    )
    op.add_column(
        "prisoners",
        sa.Column("enrichment_country_code", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "prisoners",
        sa.Column("enrichment_asn", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "prisoners",
        sa.Column("enrichment_reputation_severity", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "prisoners",
        sa.Column("enrichment_reputation_confidence", sa.Integer(), nullable=True),
    )
    op.add_column(
        "prisoners",
        sa.Column("enrichment_reason_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "prisoners",
        sa.Column("enrichment_provider", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "prisoners",
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "enrichment_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_enrichment_jobs_claim_fifo",
        "enrichment_jobs",
        ["status", "available_at", "created_at", "id"],
    )
    op.create_index(
        "ix_enrichment_jobs_prisoner_created",
        "enrichment_jobs",
        ["prisoner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_enrichment_jobs_prisoner_created", table_name="enrichment_jobs")
    op.drop_index("ix_enrichment_jobs_claim_fifo", table_name="enrichment_jobs")
    op.drop_table("enrichment_jobs")

    op.drop_column("prisoners", "last_enriched_at")
    op.drop_column("prisoners", "enrichment_provider")
    op.drop_column("prisoners", "enrichment_reason_metadata")
    op.drop_column("prisoners", "enrichment_reputation_confidence")
    op.drop_column("prisoners", "enrichment_reputation_severity")
    op.drop_column("prisoners", "enrichment_asn")
    op.drop_column("prisoners", "enrichment_country_code")
    op.drop_column("prisoners", "enrichment_status")
