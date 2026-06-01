from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import LessonProgress
from app.models.gamification import UserActivityDay
from app.models.user import User

TRACKED_ACTIVITY_TYPES = {
    "site",
    "dashboard",
    "lesson",
    "course",
    "pvp",
    "quests",
    "shop",
    "profile",
    "admin",
    "general",
}
MAX_HEARTBEAT_SECONDS = 60


def today_utc() -> date:
    return datetime.now(UTC).date()


def day_start(day: date | None = None) -> datetime:
    return datetime.combine(day or today_utc(), time.min, tzinfo=UTC)


def sanitize_activity_type(activity_type: str | None) -> str:
    if not activity_type:
        return "general"
    activity_type = activity_type.strip().lower().replace("-", "_")[:40]
    return activity_type if activity_type in TRACKED_ACTIVITY_TYPES else "general"


def sanitize_seconds(seconds: int | None) -> int:
    if seconds is None:
        return 0
    return max(0, min(int(seconds), MAX_HEARTBEAT_SECONDS))


async def add_activity_seconds(
    db: AsyncSession,
    user: User,
    activity_type: str,
    seconds: int,
    activity_date: date | None = None,
) -> UserActivityDay | None:
    seconds = sanitize_seconds(seconds)
    if seconds <= 0:
        return None

    activity_type = sanitize_activity_type(activity_type)
    activity_date = activity_date or today_utc()
    row = await db.scalar(
        select(UserActivityDay).where(
            UserActivityDay.user_id == user.id,
            UserActivityDay.activity_date == activity_date,
            UserActivityDay.activity_type == activity_type,
        )
    )
    if row is None:
        row = UserActivityDay(
            user_id=user.id,
            activity_date=activity_date,
            activity_type=activity_type,
            seconds=0,
        )
        db.add(row)
        await db.flush()
    row.seconds += seconds
    return row


async def add_heartbeat_activity(
    db: AsyncSession,
    user: User,
    activity_type: str,
    seconds: int,
    reference_id: int | None = None,
) -> None:
    seconds = sanitize_seconds(seconds)
    if seconds <= 0:
        return

    activity_type = sanitize_activity_type(activity_type)
    await add_activity_seconds(db, user, "site", seconds)
    if activity_type != "site":
        await add_activity_seconds(db, user, activity_type, seconds)

    if activity_type == "lesson" and reference_id:
        progress = await db.scalar(
            select(LessonProgress).where(
                LessonProgress.user_id == user.id,
                LessonProgress.lesson_id == reference_id,
            )
        )
        if progress is None:
            progress = LessonProgress(
                user_id=user.id, lesson_id=reference_id, watched_seconds=0
            )
            db.add(progress)
            await db.flush()
        progress.watched_seconds = int(progress.watched_seconds or 0) + seconds


async def get_activity_summary(
    db: AsyncSession, user: User, day: date | None = None
) -> dict[str, Any]:
    day = day or today_utc()
    rows = (
        (
            await db.execute(
                select(UserActivityDay).where(
                    UserActivityDay.user_id == user.id,
                    UserActivityDay.activity_date == day,
                )
            )
        )
        .scalars()
        .all()
    )
    by_type = {row.activity_type: row.seconds for row in rows}
    return {
        "date": day,
        "site_seconds": by_type.get("site", 0),
        "lesson_seconds": by_type.get("lesson", 0),
        "course_seconds": by_type.get("course", 0),
        "pvp_seconds": by_type.get("pvp", 0),
        "quests_seconds": by_type.get("quests", 0),
        "shop_seconds": by_type.get("shop", 0),
        "profile_seconds": by_type.get("profile", 0),
        "by_type": by_type,
    }


async def get_activity_total_seconds(
    db: AsyncSession, user: User, days: int = 14
) -> int:
    start = today_utc() - timedelta(days=days - 1)
    total = await db.scalar(
        select(func.coalesce(func.sum(UserActivityDay.seconds), 0)).where(
            UserActivityDay.user_id == user.id,
            UserActivityDay.activity_date >= start,
            UserActivityDay.activity_type == "site",
        )
    )
    return int(total or 0)
