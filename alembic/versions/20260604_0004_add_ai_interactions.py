"""Add AI interactions

Revision ID: 20260604_0004
Revises: 20260603_0003
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "20260604_0004"
down_revision = "20260603_0003"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("ai_interactions"):
        return
    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("context_type", sa.String(length=40), nullable=False),
        sa.Column("context_id", sa.Integer(), nullable=True),
        sa.Column("prompt_type", sa.String(length=60), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_ai_interactions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_interactions"),
    )


def downgrade() -> None:
    if _has_table("ai_interactions"):
        op.drop_table("ai_interactions")
