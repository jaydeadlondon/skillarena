from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import LessonProgress
from app.models.gamification import Achievement, UserAchievement
from app.models.pvp import PvpBattle
from app.models.user import User
from app.services.rewards import add_skill_points


async def unlock_achievement(db: AsyncSession, user: User, code: str) -> bool:
    achievement = await db.scalar(select(Achievement).where(Achievement.code == code))
    if achievement is None:
        return False

    existing = await db.scalar(
        select(UserAchievement).where(
            UserAchievement.user_id == user.id,
            UserAchievement.achievement_id == achievement.id,
        )
    )
    if existing is not None:
        return False

    db.add(UserAchievement(user_id=user.id, achievement_id=achievement.id))
    if achievement.reward_points:
        await add_skill_points(
            db,
            user,
            achievement.reward_points,
            f"Achievement unlocked: {achievement.title}",
            "achievement",
            achievement.id,
        )
    return True


async def evaluate_learning_achievements(db: AsyncSession, user: User) -> list[str]:
    unlocked: list[str] = []

    completed_lessons = await db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.completed.is_(True),
        )
    )
    completed_lessons = int(completed_lessons or 0)

    total_study_seconds = await db.scalar(
        select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
            LessonProgress.user_id == user.id,
        )
    )
    total_study_minutes = int(total_study_seconds or 0) // 60

    checks = [
        (completed_lessons >= 1, "first_lesson"),
        (completed_lessons >= 5, "five_lessons"),
        (total_study_minutes >= 10, "ten_study_minutes"),
        (total_study_minutes >= 60, "one_study_hour"),
    ]
    for condition, code in checks:
        if condition and await unlock_achievement(db, user, code):
            unlocked.append(code)

    unlocked.extend(await evaluate_balance_achievement(db, user))
    return unlocked


async def evaluate_pvp_achievements(db: AsyncSession, user: User) -> list[str]:
    unlocked: list[str] = []

    participated = await db.scalar(
        select(func.count(PvpBattle.id)).where(
            (PvpBattle.challenger_id == user.id) | (PvpBattle.opponent_id == user.id)
        )
    )
    wins = await db.scalar(
        select(func.count(PvpBattle.id)).where(PvpBattle.winner_id == user.id)
    )

    checks = [
        (int(participated or 0) >= 1, "first_duel"),
        (int(wins or 0) >= 1, "first_pvp_win"),
        (int(wins or 0) >= 5, "five_pvp_wins"),
    ]
    for condition, code in checks:
        if condition and await unlock_achievement(db, user, code):
            unlocked.append(code)
    return unlocked


async def evaluate_balance_achievement(db: AsyncSession, user: User) -> list[str]:
    two_weeks_ago = datetime.now(UTC) - timedelta(days=14)
    study_seconds_2w = await db.scalar(
        select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.updated_at >= two_weeks_ago,
        )
    )
    study_minutes_2w = int(study_seconds_2w or 0) // 60
    if study_minutes_2w > user.steam_playtime_2w_minutes and study_minutes_2w > 0:
        if await unlock_achievement(db, user, "study_over_steam"):
            return ["study_over_steam"]
    return []


async def evaluate_all_achievements(db: AsyncSession, user: User) -> list[str]:
    unlocked = []
    unlocked.extend(await evaluate_learning_achievements(db, user))
    unlocked.extend(await evaluate_pvp_achievements(db, user))
    return unlocked
