"""Add course content metadata

Revision ID: 20260607_0008
Revises: 20260606_0007
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "20260607_0008"
down_revision = "20260606_0007"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        column["name"] for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    if not _has_column("courses", "difficulty"):
        op.add_column(
            "courses",
            sa.Column(
                "difficulty",
                sa.String(length=40),
                nullable=False,
                server_default="beginner",
            ),
        )
    if not _has_column("courses", "estimated_minutes"):
        op.add_column(
            "courses",
            sa.Column(
                "estimated_minutes", sa.Integer(), nullable=False, server_default="60"
            ),
        )
    if not _has_column("courses", "is_featured"):
        op.add_column(
            "courses",
            sa.Column(
                "is_featured", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )


def downgrade() -> None:
    if _has_column("courses", "is_featured"):
        op.drop_column("courses", "is_featured")
    if _has_column("courses", "estimated_minutes"):
        op.drop_column("courses", "estimated_minutes")
    if _has_column("courses", "difficulty"):
        op.drop_column("courses", "difficulty")
