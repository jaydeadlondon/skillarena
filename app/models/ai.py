from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    context_type: Mapped[str] = mapped_column(String(40), nullable=False)
    context_id: Mapped[int | None] = mapped_column(Integer)
    prompt_type: Mapped[str] = mapped_column(String(60), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[created_at]

    user = relationship("User", back_populates="ai_interactions")
