"""Convert prisoner identity to canonical source-ip model with protocol history."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_03"
down_revision = "20260303_02"
branch_labels = None
depends_on = None


def _attempt_expr(alias: str) -> str:
    return f"""
    CASE
      WHEN COALESCE({alias}.credential_count, 0) + COALESCE({alias}.command_count, 0) + COALESCE({alias}.download_count, 0) > 0
      THEN COALESCE({alias}.credential_count, 0) + COALESCE({alias}.command_count, 0) + COALESCE({alias}.download_count, 0)
      ELSE 1
    END
    """


def upgrade() -> None:
    op.rename_table("prisoners", "prisoners_legacy")

    op.create_table(
        "prisoners",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("credential_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("command_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("source_ip", name="uq_prisoner_source_ip"),
    )

    op.create_table(
        "prisoner_protocol_activities",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("prisoner_id", "protocol", name="uq_prisoner_protocol_activity_identity"),
    )

    op.create_table(
        "prisoner_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("credential", sa.String(length=256), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "prisoner_commands",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("command", sa.String(length=2048), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "prisoner_downloads",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("download_url", sa.String(length=2048), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners.id"], ondelete="CASCADE"),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            f"""
            INSERT INTO prisoners (
                source_ip,
                country_code,
                attempt_count,
                first_seen_at,
                last_seen_at,
                credential_count,
                command_count,
                download_count
            )
            SELECT
                source_ip,
                NULL AS country_code,
                SUM({_attempt_expr("legacy")}) AS attempt_count,
                MIN(first_seen_at) AS first_seen_at,
                MAX(last_seen_at) AS last_seen_at,
                SUM(COALESCE(credential_count, 0)) AS credential_count,
                SUM(COALESCE(command_count, 0)) AS command_count,
                SUM(COALESCE(download_count, 0)) AS download_count
            FROM prisoners_legacy AS legacy
            GROUP BY source_ip
            """
        )
    )

    connection.execute(
        sa.text(
            f"""
            INSERT INTO prisoner_protocol_activities (
                prisoner_id,
                protocol,
                attempt_count,
                first_seen_at,
                last_seen_at
            )
            SELECT
                p.id AS prisoner_id,
                legacy.protocol AS protocol,
                SUM({_attempt_expr("legacy")}) AS attempt_count,
                MIN(legacy.first_seen_at) AS first_seen_at,
                MAX(legacy.last_seen_at) AS last_seen_at
            FROM prisoners_legacy AS legacy
            JOIN prisoners AS p
              ON p.source_ip = legacy.source_ip
            GROUP BY p.id, legacy.protocol
            """
        )
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Postgres keeps unique-constraint names schema-wide. Drop the legacy
        # name before creating the replacement table with the same constraint.
        op.drop_constraint("uq_ingest_delivery_id", "ingest_deliveries", type_="unique")

    op.create_table(
        "ingest_deliveries_new",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("delivery_id", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("delivery_id", name="uq_ingest_delivery_id"),
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO ingest_deliveries_new (id, delivery_id, protocol, source_ip, prisoner_id, created_at)
            SELECT
                d.id,
                d.delivery_id,
                d.protocol,
                d.source_ip,
                p.id AS prisoner_id,
                d.created_at
            FROM ingest_deliveries AS d
            LEFT JOIN prisoners_legacy AS legacy
              ON legacy.id = d.prisoner_id
            LEFT JOIN prisoners AS p
              ON p.source_ip = COALESCE(legacy.source_ip, d.source_ip)
            """
        )
    )

    op.drop_table("ingest_deliveries")
    op.rename_table("ingest_deliveries_new", "ingest_deliveries")
    op.drop_table("prisoners_legacy")


def downgrade() -> None:
    op.create_table(
        "prisoners_legacy",
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

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO prisoners_legacy (
                source_ip,
                protocol,
                first_seen_at,
                last_seen_at,
                credential_count,
                command_count,
                download_count
            )
            SELECT
                p.source_ip,
                activity.protocol,
                activity.first_seen_at,
                activity.last_seen_at,
                0 AS credential_count,
                0 AS command_count,
                0 AS download_count
            FROM prisoner_protocol_activities AS activity
            JOIN prisoners AS p
              ON p.id = activity.prisoner_id
            """
        )
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Mirror the upgrade behavior so downgrade can recreate the legacy
        # ingest_deliveries table with the canonical unique-constraint name.
        op.drop_constraint("uq_ingest_delivery_id", "ingest_deliveries", type_="unique")

    op.create_table(
        "ingest_deliveries_legacy",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("delivery_id", sa.String(length=64), nullable=False),
        sa.Column("protocol", sa.String(length=16), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("prisoner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prisoner_id"], ["prisoners_legacy.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("delivery_id", name="uq_ingest_delivery_id"),
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO ingest_deliveries_legacy (id, delivery_id, protocol, source_ip, prisoner_id, created_at)
            SELECT
                d.id,
                d.delivery_id,
                d.protocol,
                d.source_ip,
                legacy.id AS prisoner_id,
                d.created_at
            FROM ingest_deliveries AS d
            LEFT JOIN prisoners AS p
              ON p.id = d.prisoner_id
            LEFT JOIN prisoners_legacy AS legacy
              ON legacy.source_ip = COALESCE(p.source_ip, d.source_ip)
             AND legacy.protocol = d.protocol
            """
        )
    )

    op.drop_table("ingest_deliveries")
    op.rename_table("ingest_deliveries_legacy", "ingest_deliveries")

    op.drop_table("prisoner_downloads")
    op.drop_table("prisoner_commands")
    op.drop_table("prisoner_credentials")
    op.drop_table("prisoner_protocol_activities")
    op.drop_table("prisoners")
    op.rename_table("prisoners_legacy", "prisoners")
