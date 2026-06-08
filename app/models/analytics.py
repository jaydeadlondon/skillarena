from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reference_type: Mapped[str | None] = mapped_column(String(80))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    event_metadata: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[created_at]

    user = relationship("User", back_populates="analytics_events")
