"""Expand onboarding preferences

Revision ID: 20260603_0003
Revises: 20260603_0002
Create Date: 2026-06-03
"""

import sqlalchemy as sa

from alembic import op

revision = "20260603_0003"
down_revision = "20260603_0002"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {
        column["name"] for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    if not _has_column("user_onboarding", "daily_goal_minutes"):
        op.add_column(
            "user_onboarding",
            sa.Column(
                "daily_goal_minutes", sa.Integer(), nullable=False, server_default="20"
            ),
        )
    if not _has_column("user_onboarding", "preferred_learning_style"):
        op.add_column(
            "user_onboarding",
            sa.Column(
                "preferred_learning_style",
                sa.String(length=40),
                nullable=False,
                server_default="video",
            ),
        )
    if not _has_column("user_onboarding", "focus_challenge"):
        op.add_column(
            "user_onboarding",
            sa.Column(
                "focus_challenge",
                sa.String(length=80),
                nullable=False,
                server_default="distractions",
            ),
        )
    if not _has_column("user_onboarding", "wants_pvp"):
        op.add_column(
            "user_onboarding",
            sa.Column(
                "wants_pvp", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
        )
    if not _has_column("user_onboarding", "wants_steam_balance"):
        op.add_column(
            "user_onboarding",
            sa.Column(
                "wants_steam_balance",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade() -> None:
    for column_name in [
        "wants_steam_balance",
        "wants_pvp",
        "focus_challenge",
        "preferred_learning_style",
        "daily_goal_minutes",
    ]:
        if _has_column("user_onboarding", column_name):
            op.drop_column("user_onboarding", column_name)
