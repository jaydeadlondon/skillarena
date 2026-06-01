from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import UserOnboarding
from app.models.user import User


async def get_user_onboarding(db: AsyncSession, user: User) -> UserOnboarding | None:
    return await db.scalar(select(UserOnboarding).where(UserOnboarding.user_id == user.id))


async def has_completed_onboarding(db: AsyncSession, user: User) -> bool:
    onboarding = await get_user_onboarding(db, user)
    return bool(onboarding and onboarding.completed)


async def save_onboarding(
    db: AsyncSession,
    user: User,
    learning_goal: str,
    experience_level: str,
    weekly_goal_minutes: int,
    preferred_session_minutes: int,
) -> UserOnboarding:
    onboarding = await get_user_onboarding(db, user)
    if onboarding is None:
        onboarding = UserOnboarding(user_id=user.id, learning_goal=learning_goal)
        db.add(onboarding)
        await db.flush()

    onboarding.learning_goal = learning_goal[:120]
    onboarding.experience_level = experience_level[:40]
    onboarding.weekly_goal_minutes = max(30, min(int(weekly_goal_minutes), 2000))
    onboarding.preferred_session_minutes = max(5, min(int(preferred_session_minutes), 120))
    onboarding.completed = True
    return onboarding
