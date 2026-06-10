from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at, updated_at


class TelegramPayment(Base):
    __tablename__ = "telegram_payments"
    __table_args__ = (UniqueConstraint("payload", name="uq_telegram_payment_payload"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    payload: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    plan_code: Mapped[str] = mapped_column(String(20), nullable=False)
    premium_days: Mapped[int] = mapped_column(Integer, nullable=False)
    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user = relationship("User", back_populates="telegram_payments")
