from datetime import UTC, datetime

from app.models.user import User, UserRole

FREE_PLAN = "free"
PREMIUM_PLAN = "premium"
VALID_PLANS = {FREE_PLAN, PREMIUM_PLAN}


def has_active_premium_until(user: User) -> bool:
    if not user.premium_until:
        return False
    premium_until = user.premium_until
    if premium_until.tzinfo is None:
        premium_until = premium_until.replace(tzinfo=UTC)
    return premium_until > datetime.now(UTC)


def normalized_plan(user: User) -> str:
    if user.role == UserRole.ADMIN:
        return PREMIUM_PLAN
    if user.plan == PREMIUM_PLAN or has_active_premium_until(user):
        return PREMIUM_PLAN
    return FREE_PLAN


def is_premium(user: User) -> bool:
    return normalized_plan(user) == PREMIUM_PLAN


def can_access_pvp(user: User) -> bool:
    return is_premium(user)


def can_access_premium_cosmetic(user: User) -> bool:
    return is_premium(user)
