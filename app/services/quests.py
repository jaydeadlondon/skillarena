from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import LessonProgress
from app.models.gamification import Quest, QuestFrequency, UserActivityDay, UserQuest
from app.models.pvp import BattleStatus, PvpBattle
from app.models.user import User
from app.services.rewards import add_skill_points


def daily_period_key(day: date | None = None) -> str:
    return (day or datetime.now(UTC).date()).isoformat()


def day_start(day: date | None = None) -> datetime:
    return datetime.combine(day or datetime.now(UTC).date(), time.min, tzinfo=UTC)


async def calculate_metric_value(db: AsyncSession, user: User, metric: str) -> int:
    start = day_start()

    if metric == "study_minutes":
        tracked_seconds = await db.scalar(
            select(func.coalesce(func.sum(UserActivityDay.seconds), 0)).where(
                UserActivityDay.user_id == user.id,
                UserActivityDay.activity_date == datetime.now(UTC).date(),
                UserActivityDay.activity_type == "lesson",
            )
        )
        progress_seconds = await db.scalar(
            select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
                LessonProgress.user_id == user.id,
                LessonProgress.updated_at >= start,
            )
        )
        return max(int(tracked_seconds or 0), int(progress_seconds or 0)) // 60

    if metric == "lessons_completed":
        count = await db.scalar(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.user_id == user.id,
                LessonProgress.completed.is_(True),
                LessonProgress.updated_at >= start,
            )
        )
        return int(count or 0)

    if metric == "pvp_wins":
        count = await db.scalar(
            select(func.count(PvpBattle.id)).where(
                PvpBattle.winner_id == user.id,
                PvpBattle.status == BattleStatus.FINISHED,
                PvpBattle.updated_at >= start,
            )
        )
        return int(count or 0)

    if metric == "pvp_participation":
        count = await db.scalar(
            select(func.count(PvpBattle.id)).where(
                (
                    (PvpBattle.challenger_id == user.id)
                    | (PvpBattle.opponent_id == user.id)
                ),
                PvpBattle.updated_at >= start,
            )
        )
        return int(count or 0)

    return 0


async def get_or_create_user_quest(
    db: AsyncSession, user: User, quest: Quest
) -> UserQuest:
    period_key = daily_period_key()
    user_quest = await db.scalar(
        select(UserQuest).where(
            UserQuest.user_id == user.id,
            UserQuest.quest_id == quest.id,
            UserQuest.period_key == period_key,
        )
    )
    if user_quest is None:
        user_quest = UserQuest(
            user_id=user.id, quest_id=quest.id, period_key=period_key
        )
        db.add(user_quest)
        await db.flush()
    return user_quest


async def sync_user_quest(db: AsyncSession, user: User, quest: Quest) -> UserQuest:
    user_quest = await get_or_create_user_quest(db, user, quest)
    value = await calculate_metric_value(db, user, quest.target_metric)
    user_quest.progress_value = min(value, quest.target_value)
    user_quest.completed = value >= quest.target_value
    return user_quest


async def get_daily_quest_cards(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    quests = (
        (
            await db.execute(
                select(Quest)
                .where(
                    Quest.is_active.is_(True), Quest.frequency == QuestFrequency.DAILY
                )
                .order_by(Quest.reward_points.desc(), Quest.title)
            )
        )
        .scalars()
        .all()
    )

    cards: list[dict[str, Any]] = []
    for quest in quests:
        user_quest = await sync_user_quest(db, user, quest)
        percent = 0
        if quest.target_value > 0:
            percent = min(
                100, int(user_quest.progress_value * 100 / quest.target_value)
            )
        cards.append(
            {
                "quest": quest,
                "user_quest": user_quest,
                "percent": percent,
                "can_claim": user_quest.completed and not user_quest.claimed,
            }
        )
    return cards


async def claim_daily_quest(
    db: AsyncSession, user: User, quest_id: int
) -> tuple[bool, str]:
    quest = await db.get(Quest, quest_id)
    if quest is None or not quest.is_active:
        return False, "quest-not-found"

    user_quest = await sync_user_quest(db, user, quest)
    if user_quest.claimed:
        return False, "already-claimed"
    if not user_quest.completed:
        return False, "not-completed"

    user_quest.claimed = True
    await add_skill_points(
        db,
        user,
        quest.reward_points,
        f"Daily quest completed: {quest.title}",
        "quest",
        quest.id,
    )
    return True, "claimed"
