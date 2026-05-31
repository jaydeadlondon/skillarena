from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at, updated_at


class QuestFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    COURSE = "course"


class AchievementType(StrEnum):
    LESSONS = "lessons"
    COURSES = "courses"
    STREAK = "streak"
    PVP_WINS = "pvp_wins"
    STUDY_MINUTES = "study_minutes"
    BALANCE = "balance"
    RETURN = "return"


class Quest(Base):
    __tablename__ = "quests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[QuestFrequency] = mapped_column(
        default=QuestFrequency.DAILY, nullable=False
    )
    target_metric: Mapped[str] = mapped_column(String(80), nullable=False)
    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user_progresses = relationship(
        "UserQuest", back_populates="quest", cascade="all, delete-orphan"
    )


class UserQuest(Base):
    __tablename__ = "user_quests"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "quest_id", "period_key", name="uq_user_quest_period"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quest_id: Mapped[int] = mapped_column(
        ForeignKey("quests.id", ondelete="CASCADE"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(32), nullable=False)
    progress_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user = relationship("User", back_populates="quest_progresses")
    quest = relationship("Quest", back_populates="user_progresses")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    achievement_type: Mapped[AchievementType] = mapped_column(nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    badge_icon: Mapped[str] = mapped_column(String(20), default="🏆", nullable=False)
    created_at: Mapped[created_at]

    users = relationship(
        "UserAchievement", back_populates="achievement", cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[created_at]

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="users")


class CosmeticItem(Base):
    __tablename__ = "cosmetic_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    item_type: Mapped[str] = mapped_column(
        String(40), nullable=False
    )  # frame, background, cursor, etc.
    price_points: Mapped[int] = mapped_column(Integer, nullable=False)
    preview_value: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
