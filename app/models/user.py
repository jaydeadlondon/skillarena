from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at, updated_at


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    steam_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.USER, nullable=False
    )
    skill_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selected_title: Mapped[str | None] = mapped_column(String(80))
    selected_frame: Mapped[str | None] = mapped_column(String(80))
    focus_mode_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    steam_playtime_2w_minutes: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    progresses = relationship(
        "LessonProgress", back_populates="user", cascade="all, delete-orphan"
    )
    quest_progresses = relationship(
        "UserQuest", back_populates="user", cascade="all, delete-orphan"
    )
    achievements = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )
    currency_transactions = relationship("CurrencyTransaction", back_populates="user")
    cosmetics = relationship(
        "UserCosmetic", back_populates="user", cascade="all, delete-orphan"
    )
    streak_days = relationship(
        "UserStreakDay", back_populates="user", cascade="all, delete-orphan"
    )
    activity_days = relationship(
        "UserActivityDay", back_populates="user", cascade="all, delete-orphan"
    )
    focus_sessions = relationship(
        "FocusSession", back_populates="user", cascade="all, delete-orphan"
    )
    onboarding = relationship(
        "UserOnboarding",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    notifications = relationship(
        "UserNotification", back_populates="user", cascade="all, delete-orphan"
    )
    ai_interactions = relationship(
        "AIInteraction", back_populates="user", cascade="all, delete-orphan"
    )
    admin_audit_logs = relationship("AdminAuditLog", back_populates="admin_user")


class CurrencyTransaction(Base):
    __tablename__ = "currency_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(160), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(80))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[created_at]

    user = relationship("User", back_populates="currency_transactions")
