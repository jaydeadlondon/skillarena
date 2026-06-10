"""Add Telegram Stars payments

Revision ID: 20260608_0009
Revises: 20260607_0008
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "20260608_0009"
down_revision = "20260607_0008"
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
    if not _has_column("users", "premium_until"):
        op.add_column(
            "users",
            sa.Column("premium_until", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_table("telegram_payments"):
        op.create_table(
            "telegram_payments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("telegram_user_id", sa.BigInteger(), nullable=True),
            sa.Column("payload", sa.String(length=120), nullable=False),
            sa.Column(
                "status", sa.String(length=40), nullable=False, server_default="pending"
            ),
            sa.Column("plan_code", sa.String(length=20), nullable=False),
            sa.Column("premium_days", sa.Integer(), nullable=False),
            sa.Column("stars_amount", sa.Integer(), nullable=False),
            sa.Column("raw_payload", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_telegram_payments_user_id_users",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_telegram_payments"),
            sa.UniqueConstraint("payload", name="uq_telegram_payment_payload"),
        )


def downgrade() -> None:
    if _has_table("telegram_payments"):
        op.drop_table("telegram_payments")
    if _has_column("users", "premium_until"):
        op.drop_column("users", "premium_until")
