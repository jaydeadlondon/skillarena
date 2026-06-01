from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import LessonProgress
from app.models.gamification import UserStreakDay
from app.models.pvp import BattleStatus, PvpBattle
from app.models.user import User
from app.services.achievements import unlock_achievement

MIN_STUDY_SECONDS_FOR_STREAK = 10 * 60


def today_utc() -> date:
    return datetime.now(UTC).date()


def date_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def date_end(day: date) -> datetime:
    return date_start(day) + timedelta(days=1)


async def calculate_day_activity(
    db: AsyncSession, user: User, day: date
) -> dict[str, int | bool]:
    start = date_start(day)
    end = date_end(day)

    study_seconds = await db.scalar(
        select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.updated_at >= start,
            LessonProgress.updated_at < end,
        )
    )
    lessons_completed = await db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.completed.is_(True),
            LessonProgress.updated_at >= start,
            LessonProgress.updated_at < end,
        )
    )
    pvp_wins = await db.scalar(
        select(func.count(PvpBattle.id)).where(
            PvpBattle.winner_id == user.id,
            PvpBattle.status == BattleStatus.FINISHED,
            PvpBattle.updated_at >= start,
            PvpBattle.updated_at < end,
        )
    )

    study_seconds = int(study_seconds or 0)
    lessons_completed = int(lessons_completed or 0)
    pvp_wins = int(pvp_wins or 0)
    qualified = (
        study_seconds >= MIN_STUDY_SECONDS_FOR_STREAK
        or lessons_completed >= 1
        or pvp_wins >= 1
    )
    return {
        "study_seconds": study_seconds,
        "lessons_completed": lessons_completed,
        "pvp_wins": pvp_wins,
        "qualified": qualified,
    }


async def get_or_create_streak_day(
    db: AsyncSession, user: User, day: date
) -> UserStreakDay:
    streak_day = await db.scalar(
        select(UserStreakDay).where(
            UserStreakDay.user_id == user.id, UserStreakDay.activity_date == day
        )
    )
    if streak_day is None:
        streak_day = UserStreakDay(user_id=user.id, activity_date=day)
        db.add(streak_day)
        await db.flush()
    return streak_day


async def sync_streak_day(
    db: AsyncSession, user: User, day: date | None = None
) -> UserStreakDay:
    day = day or today_utc()
    activity = await calculate_day_activity(db, user, day)
    streak_day = await get_or_create_streak_day(db, user, day)
    streak_day.study_seconds = int(activity["study_seconds"])
    streak_day.lessons_completed = int(activity["lessons_completed"])
    streak_day.pvp_wins = int(activity["pvp_wins"])
    streak_day.qualified = bool(activity["qualified"])
    return streak_day


async def recalculate_user_streak(db: AsyncSession, user: User) -> int:
    today = today_utc()
    qualified_days = (
        (
            await db.execute(
                select(UserStreakDay.activity_date)
                .where(
                    UserStreakDay.user_id == user.id, UserStreakDay.qualified.is_(True)
                )
                .order_by(UserStreakDay.activity_date.desc())
            )
        )
        .scalars()
        .all()
    )
    qualified_set = set(qualified_days)

    if today in qualified_set:
        cursor = today
    elif today - timedelta(days=1) in qualified_set:
        cursor = today - timedelta(days=1)
    else:
        user.current_streak_days = 0
        return 0

    streak = 0
    while cursor in qualified_set:
        streak += 1
        cursor -= timedelta(days=1)

    user.current_streak_days = streak
    user.best_streak_days = max(user.best_streak_days or 0, streak)

    if streak >= 3:
        await unlock_achievement(db, user, "three_day_streak")
    if streak >= 7:
        await unlock_achievement(db, user, "seven_day_streak")

    return streak


async def sync_user_streak(
    db: AsyncSession, user: User, day: date | None = None
) -> int:
    await sync_streak_day(db, user, day)
    return await recalculate_user_streak(db, user)


async def get_streak_timeline(
    db: AsyncSession, user: User, days: int = 14
) -> list[dict[str, Any]]:
    today = today_utc()
    start = today - timedelta(days=days - 1)
    rows = (
        (
            await db.execute(
                select(UserStreakDay).where(
                    UserStreakDay.user_id == user.id,
                    UserStreakDay.activity_date >= start,
                    UserStreakDay.activity_date <= today,
                )
            )
        )
        .scalars()
        .all()
    )
    by_date = {row.activity_date: row for row in rows}

    timeline = []
    for index in range(days):
        day = start + timedelta(days=index)
        row = by_date.get(day)
        timeline.append(
            {
                "date": day,
                "day_label": day.strftime("%a"),
                "qualified": bool(row and row.qualified),
                "study_minutes": int((row.study_seconds if row else 0) / 60),
                "lessons_completed": row.lessons_completed if row else 0,
                "pvp_wins": row.pvp_wins if row else 0,
                "is_today": day == today,
            }
        )
    return timeline
