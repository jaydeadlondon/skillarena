from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, LessonProgress
from app.models.gamification import Achievement, AchievementType, UserAchievement
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


async def _completed_courses_count(db: AsyncSession, user: User) -> int:
    courses = (
        (
            await db.execute(
                select(Course)
                .where(Course.is_published.is_(True))
                .options(selectinload(Course.lessons))
            )
        )
        .scalars()
        .all()
    )
    progresses = (
        (
            await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == user.id,
                    LessonProgress.completed.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    completed_lesson_ids = {progress.lesson_id for progress in progresses}
    completed_courses = 0
    for course in courses:
        lesson_ids = {lesson.id for lesson in course.lessons}
        if lesson_ids and lesson_ids.issubset(completed_lesson_ids):
            completed_courses += 1
    return completed_courses


async def achievement_metric_value(
    db: AsyncSession, user: User, achievement: Achievement
) -> int:
    if achievement.code == "first_duel":
        participated = await db.scalar(
            select(func.count(PvpBattle.id)).where(
                (PvpBattle.challenger_id == user.id)
                | (PvpBattle.opponent_id == user.id)
            )
        )
        return int(participated or 0)

    if achievement.achievement_type == AchievementType.LESSONS:
        value = await db.scalar(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.user_id == user.id,
                LessonProgress.completed.is_(True),
            )
        )
        return int(value or 0)

    if achievement.achievement_type == AchievementType.COURSES:
        return await _completed_courses_count(db, user)

    if achievement.achievement_type == AchievementType.STREAK:
        return int(user.current_streak_days or 0)

    if achievement.achievement_type == AchievementType.PVP_WINS:
        value = await db.scalar(
            select(func.count(PvpBattle.id)).where(PvpBattle.winner_id == user.id)
        )
        return int(value or 0)

    if achievement.achievement_type == AchievementType.STUDY_MINUTES:
        seconds = await db.scalar(
            select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
                LessonProgress.user_id == user.id,
            )
        )
        return int(seconds or 0) // 60

    if achievement.achievement_type == AchievementType.BALANCE:
        two_weeks_ago = datetime.now(UTC) - timedelta(days=14)
        study_seconds_2w = await db.scalar(
            select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
                LessonProgress.user_id == user.id,
                LessonProgress.updated_at >= two_weeks_ago,
            )
        )
        study_minutes_2w = int(study_seconds_2w or 0) // 60
        return (
            1
            if study_minutes_2w > user.steam_playtime_2w_minutes
            and study_minutes_2w > 0
            else 0
        )

    return 0


def achievement_group_label(achievement_type: AchievementType) -> str:
    labels = {
        AchievementType.LESSONS: "Learning",
        AchievementType.COURSES: "Courses",
        AchievementType.STREAK: "Streaks",
        AchievementType.PVP_WINS: "PvP",
        AchievementType.STUDY_MINUTES: "Study Time",
        AchievementType.BALANCE: "Balance",
        AchievementType.RETURN: "Return",
    }
    return labels.get(achievement_type, achievement_type.value.title())


async def get_achievement_gallery(db: AsyncSession, user: User) -> dict[str, Any]:
    await evaluate_all_achievements(db, user)

    achievements = (
        (
            await db.execute(
                select(Achievement).order_by(
                    Achievement.achievement_type, Achievement.threshold
                )
            )
        )
        .scalars()
        .all()
    )
    unlocked_rows = (
        (
            await db.execute(
                select(UserAchievement).where(UserAchievement.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    unlocked_ids = {row.achievement_id for row in unlocked_rows}

    cards: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for achievement in achievements:
        value = await achievement_metric_value(db, user, achievement)
        target = max(int(achievement.threshold), 1)
        unlocked = achievement.id in unlocked_ids
        percent = 100 if unlocked else min(100, int(value * 100 / target))
        card = {
            "achievement": achievement,
            "unlocked": unlocked,
            "current": min(value, target),
            "raw_current": value,
            "target": target,
            "percent": percent,
            "group": achievement_group_label(achievement.achievement_type),
        }
        cards.append(card)
        grouped[card["group"]].append(card)

    unlocked_count = sum(1 for card in cards if card["unlocked"])
    return {
        "cards": cards,
        "grouped": dict(grouped),
        "unlocked_count": unlocked_count,
        "total_count": len(cards),
        "locked_count": len(cards) - unlocked_count,
        "completion_percent": int(unlocked_count * 100 / len(cards)) if cards else 0,
    }
