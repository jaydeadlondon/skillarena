"""Add premium plans and PvP contests

Revision ID: 20260606_0007
Revises: 20260605_0006
Create Date: 2026-06-06
"""

from alembic import op
import sqlalchemy as sa

revision = "20260606_0007"
down_revision = "20260605_0006"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        column["name"] for column in inspector.get_columns(table_name)
    }


def upgrade() -> None:
    if not _has_column("users", "plan"):
        op.add_column(
            "users",
            sa.Column(
                "plan", sa.String(length=20), nullable=False, server_default="free"
            ),
        )
    if not _has_column("cosmetic_items", "is_premium"):
        op.add_column(
            "cosmetic_items",
            sa.Column(
                "is_premium", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )

    if not _has_table("pvp_contests"):
        op.create_table(
            "pvp_contests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column(
                "status",
                sa.Enum("DRAFT", "ACTIVE", "FINISHED", name="pvpconteststatus"),
                nullable=False,
                server_default="ACTIVE",
            ),
            sa.Column(
                "reward_points", sa.Integer(), nullable=False, server_default="100"
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name="pk_pvp_contests"),
        )
    if not _has_table("pvp_contest_entries"):
        op.create_table(
            "pvp_contest_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("contest_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["contest_id"],
                ["pvp_contests.id"],
                name="fk_pvp_contest_entries_contest_id_pvp_contests",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_pvp_contest_entries_user_id_users",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_pvp_contest_entries"),
            sa.UniqueConstraint("contest_id", "user_id", name="uq_pvp_contest_user"),
        )


def downgrade() -> None:
    if _has_table("pvp_contest_entries"):
        op.drop_table("pvp_contest_entries")
    if _has_table("pvp_contests"):
        op.drop_table("pvp_contests")
    if _has_column("cosmetic_items", "is_premium"):
        op.drop_column("cosmetic_items", "is_premium")
    if _has_column("users", "plan"):
        op.drop_column("users", "plan")
