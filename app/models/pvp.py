from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at, updated_at


class BattleStatus(StrEnum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class PvpQuestion(Base):
    __tablename__ = "pvp_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL")
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(255), nullable=False)
    option_b: Mapped[str] = mapped_column(String(255), nullable=False)
    option_c: Mapped[str] = mapped_column(String(255), nullable=False)
    option_d: Mapped[str] = mapped_column(String(255), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]


class PvpBattle(Base):
    __tablename__ = "pvp_battles"

    id: Mapped[int] = mapped_column(primary_key=True)
    challenger_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    opponent_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    winner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[BattleStatus] = mapped_column(
        default=BattleStatus.WAITING, nullable=False
    )
    entry_fee_points: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    challenger_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opponent_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    challenger = relationship("User", foreign_keys=[challenger_id])
    opponent = relationship("User", foreign_keys=[opponent_id])
    winner = relationship("User", foreign_keys=[winner_id])
