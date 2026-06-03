"""Add server authoritative PvP deadlines

Revision ID: 20260603_0002
Revises: 20260602_0001
Create Date: 2026-06-03
"""

import sqlalchemy as sa

from alembic import op

revision = "20260603_0002"
down_revision = "20260602_0001"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {
        column["name"] for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    if not _has_column("pvp_battles", "started_at"):
        op.add_column(
            "pvp_battles",
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column("pvp_battles", "deadline_at"):
        op.add_column(
            "pvp_battles",
            sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _has_column("pvp_battles", "deadline_at"):
        op.drop_column("pvp_battles", "deadline_at")
    if _has_column("pvp_battles", "started_at"):
        op.drop_column("pvp_battles", "started_at")
