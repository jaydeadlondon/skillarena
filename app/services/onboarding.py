from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import UserOnboarding
from app.models.user import User

ALLOWED_EXPERIENCE_LEVELS = {"beginner", "intermediate", "advanced"}
ALLOWED_LEARNING_STYLES = {"video", "reading", "practice", "mixed"}
ALLOWED_FOCUS_CHALLENGES = {
    "distractions",
    "procrastination",
    "overwhelm",
    "consistency",
    "time_management",
}


async def get_user_onboarding(db: AsyncSession, user: User) -> UserOnboarding | None:
    return await db.scalar(
        select(UserOnboarding).where(UserOnboarding.user_id == user.id)
    )


async def has_completed_onboarding(db: AsyncSession, user: User) -> bool:
    onboarding = await get_user_onboarding(db, user)
    return bool(onboarding and onboarding.completed)


def clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(int(value), max_value))


async def save_onboarding(
    db: AsyncSession,
    user: User,
    learning_goal: str,
    experience_level: str,
    weekly_goal_minutes: int,
    preferred_session_minutes: int,
    daily_goal_minutes: int = 20,
    preferred_learning_style: str = "video",
    focus_challenge: str = "distractions",
    wants_pvp: bool = True,
    wants_steam_balance: bool = True,
) -> UserOnboarding:
    onboarding = await get_user_onboarding(db, user)
    if onboarding is None:
        onboarding = UserOnboarding(user_id=user.id, learning_goal=learning_goal)
        db.add(onboarding)
        await db.flush()

    if experience_level not in ALLOWED_EXPERIENCE_LEVELS:
        experience_level = "beginner"
    if preferred_learning_style not in ALLOWED_LEARNING_STYLES:
        preferred_learning_style = "video"
    if focus_challenge not in ALLOWED_FOCUS_CHALLENGES:
        focus_challenge = "distractions"

    onboarding.learning_goal = learning_goal[:120]
    onboarding.experience_level = experience_level[:40]
    onboarding.weekly_goal_minutes = clamp_int(weekly_goal_minutes, 30, 2000)
    onboarding.daily_goal_minutes = clamp_int(daily_goal_minutes, 5, 240)
    onboarding.preferred_session_minutes = clamp_int(preferred_session_minutes, 5, 120)
    onboarding.preferred_learning_style = preferred_learning_style[:40]
    onboarding.focus_challenge = focus_challenge[:80]
    onboarding.wants_pvp = bool(wants_pvp)
    onboarding.wants_steam_balance = bool(wants_steam_balance)
    onboarding.completed = True
    return onboarding
