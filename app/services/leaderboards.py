from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import LessonProgress
from app.models.gamification import FocusSession
from app.models.pvp import PvpBattle
from app.models.user import User

LEADERBOARD_LIMIT = 10


def week_start_datetime() -> datetime:
    today = datetime.now(UTC).date()
    start = today - timedelta(days=today.weekday())
    return datetime.combine(start, time.min, tzinfo=UTC)


def user_payload(user: User, value: int | float, suffix: str = "") -> dict[str, Any]:
    return {
        "user": user,
        "value": value,
        "suffix": suffix,
    }


async def top_skill_points(
    db: AsyncSession, limit: int = LEADERBOARD_LIMIT
) -> list[dict[str, Any]]:
    users = (
        (
            await db.execute(
                select(User)
                .order_by(desc(User.skill_points), User.display_name)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [user_payload(user, user.skill_points, "SP") for user in users]


async def top_current_streaks(
    db: AsyncSession, limit: int = LEADERBOARD_LIMIT
) -> list[dict[str, Any]]:
    users = (
        (
            await db.execute(
                select(User)
                .order_by(
                    desc(User.current_streak_days),
                    desc(User.best_streak_days),
                    User.display_name,
                )
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [user_payload(user, user.current_streak_days, "days") for user in users]


async def top_study_time(
    db: AsyncSession, limit: int = LEADERBOARD_LIMIT
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(
                User,
                func.coalesce(func.sum(LessonProgress.watched_seconds), 0).label(
                    "seconds"
                ),
            )
            .join(LessonProgress, LessonProgress.user_id == User.id, isouter=True)
            .group_by(User.id)
            .order_by(desc("seconds"), User.display_name)
            .limit(limit)
        )
    ).all()
    return [
        user_payload(user, round(int(seconds or 0) / 3600, 1), "h")
        for user, seconds in rows
    ]


async def top_focus_time(
    db: AsyncSession, limit: int = LEADERBOARD_LIMIT
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(
                User,
                func.coalesce(func.sum(FocusSession.duration_minutes), 0).label(
                    "minutes"
                ),
            )
            .join(FocusSession, FocusSession.user_id == User.id, isouter=True)
            .group_by(User.id)
            .order_by(desc("minutes"), User.display_name)
            .limit(limit)
        )
    ).all()
    return [user_payload(user, int(minutes or 0), "min") for user, minutes in rows]


async def top_pvp_wins(
    db: AsyncSession, limit: int = LEADERBOARD_LIMIT
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(User, func.count(PvpBattle.id).label("wins"))
            .join(PvpBattle, PvpBattle.winner_id == User.id, isouter=True)
            .group_by(User.id)
            .order_by(desc("wins"), User.display_name)
            .limit(limit)
        )
    ).all()
    return [user_payload(user, int(wins or 0), "wins") for user, wins in rows]


async def weekly_study_time(
    db: AsyncSession, limit: int = LEADERBOARD_LIMIT
) -> list[dict[str, Any]]:
    start = week_start_datetime()
    rows = (
        await db.execute(
            select(
                User,
                func.coalesce(func.sum(LessonProgress.watched_seconds), 0).label(
                    "seconds"
                ),
            )
            .join(
                LessonProgress,
                (LessonProgress.user_id == User.id)
                & (LessonProgress.updated_at >= start),
                isouter=True,
            )
            .group_by(User.id)
            .order_by(desc("seconds"), User.display_name)
            .limit(limit)
        )
    ).all()
    return [
        user_payload(user, round(int(seconds or 0) / 60, 0), "min")
        for user, seconds in rows
    ]


async def weekly_pvp_wins(
    db: AsyncSession, limit: int = LEADERBOARD_LIMIT
) -> list[dict[str, Any]]:
    start = week_start_datetime()
    rows = (
        await db.execute(
            select(User, func.count(PvpBattle.id).label("wins"))
            .join(
                PvpBattle,
                (PvpBattle.winner_id == User.id) & (PvpBattle.updated_at >= start),
                isouter=True,
            )
            .group_by(User.id)
            .order_by(desc("wins"), User.display_name)
            .limit(limit)
        )
    ).all()
    return [user_payload(user, int(wins or 0), "wins") for user, wins in rows]


async def build_leaderboards(db: AsyncSession) -> dict[str, list[dict[str, Any]]]:
    return {
        "Current Streaks": await top_current_streaks(db),
        "Skill Points": await top_skill_points(db),
        "Study Time": await top_study_time(db),
        "Focus Time": await top_focus_time(db),
        "PvP Wins": await top_pvp_wins(db),
        "Weekly Study": await weekly_study_time(db),
        "Weekly PvP Wins": await weekly_pvp_wins(db),
    }
