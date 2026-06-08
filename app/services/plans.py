from app.models.user import User, UserRole

FREE_PLAN = "free"
PREMIUM_PLAN = "premium"
VALID_PLANS = {FREE_PLAN, PREMIUM_PLAN}


def normalized_plan(user: User) -> str:
    if user.role == UserRole.ADMIN:
        return PREMIUM_PLAN
    return user.plan if user.plan in VALID_PLANS else FREE_PLAN


def is_premium(user: User) -> bool:
    return normalized_plan(user) == PREMIUM_PLAN


def can_access_pvp(user: User) -> bool:
    return is_premium(user)


def can_access_premium_cosmetic(user: User) -> bool:
    return is_premium(user)
