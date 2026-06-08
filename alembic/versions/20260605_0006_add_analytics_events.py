"""Add analytics events

Revision ID: 20260605_0006
Revises: 20260604_0005
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "20260605_0006"
down_revision = "20260604_0005"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("analytics_events"):
        return
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("reference_type", sa.String(length=80), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("event_metadata", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_analytics_events_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_events"),
    )
    op.create_index(
        "ix_analytics_events_event_type", "analytics_events", ["event_type"]
    )


def downgrade() -> None:
    if _has_table("analytics_events"):
        op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
        op.drop_table("analytics_events")
