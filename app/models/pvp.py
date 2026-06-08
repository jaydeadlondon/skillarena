from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_at, updated_at


class BattleStatus(StrEnum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class PvpContestStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    FINISHED = "finished"


class PvpContest(Base):
    __tablename__ = "pvp_contests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[PvpContestStatus] = mapped_column(
        default=PvpContestStatus.ACTIVE, nullable=False
    )
    reward_points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    entries = relationship(
        "PvpContestEntry", back_populates="contest", cascade="all, delete-orphan"
    )


class PvpContestEntry(Base):
    __tablename__ = "pvp_contest_entries"
    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_pvp_contest_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contest_id: Mapped[int] = mapped_column(
        ForeignKey("pvp_contests.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    contest = relationship("PvpContest", back_populates="entries")
    user = relationship("User")


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

    battle_links = relationship("PvpBattleQuestion", back_populates="question")


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
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    challenger = relationship("User", foreign_keys=[challenger_id])
    opponent = relationship("User", foreign_keys=[opponent_id])
    winner = relationship("User", foreign_keys=[winner_id])
    question_links = relationship(
        "PvpBattleQuestion",
        back_populates="battle",
        cascade="all, delete-orphan",
        order_by="PvpBattleQuestion.position",
    )
    submissions = relationship(
        "PvpBattleSubmission", back_populates="battle", cascade="all, delete-orphan"
    )


class PvpBattleQuestion(Base):
    __tablename__ = "pvp_battle_questions"
    __table_args__ = (
        UniqueConstraint("battle_id", "question_id", name="uq_pvp_battle_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    battle_id: Mapped[int] = mapped_column(
        ForeignKey("pvp_battles.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("pvp_questions.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[created_at]

    battle = relationship("PvpBattle", back_populates="question_links")
    question = relationship("PvpQuestion", back_populates="battle_links")


class PvpBattleSubmission(Base):
    __tablename__ = "pvp_battle_submissions"
    __table_args__ = (
        UniqueConstraint("battle_id", "user_id", name="uq_pvp_battle_submission_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    battle_id: Mapped[int] = mapped_column(
        ForeignKey("pvp_battles.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[created_at]

    battle = relationship("PvpBattle", back_populates="submissions")
    user = relationship("User")
    answers = relationship(
        "PvpBattleAnswer", back_populates="submission", cascade="all, delete-orphan"
    )


class PvpBattleAnswer(Base):
    __tablename__ = "pvp_battle_answers"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "question_id", name="uq_pvp_submission_question"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("pvp_battle_submissions.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("pvp_questions.id", ondelete="CASCADE"), nullable=False
    )
    selected_option: Mapped[str] = mapped_column(String(1), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[created_at]

    submission = relationship("PvpBattleSubmission", back_populates="answers")
    question = relationship("PvpQuestion")
