"""Add server authoritative PvP deadlines

Revision ID: 20260603_0002
Revises: 20260602_0001
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260603_0002"
down_revision = "20260602_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pvp_battles",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pvp_battles",
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pvp_battles", "deadline_at")
    op.drop_column("pvp_battles", "started_at")
