from enum import StrEnum

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(
        String(40), default="system", nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[created_at]

    user = relationship("User", back_populates="notifications")


class UserOnboarding(Base):
    __tablename__ = "user_onboarding"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_onboarding_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    learning_goal: Mapped[str] = mapped_column(String(120), nullable=False)
    experience_level: Mapped[str] = mapped_column(
        String(40), default="beginner", nullable=False
    )
    weekly_goal_minutes: Mapped[int] = mapped_column(
        Integer, default=120, nullable=False
    )
    preferred_session_minutes: Mapped[int] = mapped_column(
        Integer, default=25, nullable=False
    )
    completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user = relationship("User", back_populates="onboarding")


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]

    user = relationship("User", back_populates="focus_sessions")


class UserActivityDay(Base):
    __tablename__ = "user_activity_days"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "activity_date",
            "activity_type",
            name="uq_user_activity_day_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user = relationship("User", back_populates="activity_days")


class UserStreakDay(Base):
    __tablename__ = "user_streak_days"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_date", name="uq_user_streak_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    study_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pvp_wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user = relationship("User", back_populates="streak_days")


class CosmeticItem(Base):
    __tablename__ = "cosmetic_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    price_points: Mapped[int] = mapped_column(Integer, nullable=False)
    preview_value: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[created_at]

    owners = relationship(
        "UserCosmetic", back_populates="item", cascade="all, delete-orphan"
    )


class UserCosmetic(Base):
    __tablename__ = "user_cosmetics"
    __table_args__ = (
        UniqueConstraint("user_id", "cosmetic_item_id", name="uq_user_cosmetic_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cosmetic_item_id: Mapped[int] = mapped_column(
        ForeignKey("cosmetic_items.id", ondelete="CASCADE"), nullable=False
    )
    is_equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user = relationship("User", back_populates="cosmetics")
    item = relationship("CosmeticItem", back_populates="owners")
