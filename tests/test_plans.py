from app.models.user import User, UserRole
from app.services.plans import (
    can_access_premium_cosmetic,
    can_access_pvp,
    is_premium,
    normalized_plan,
)


def test_free_user_is_not_premium():
    user = User(steam_id="plan_free", display_name="Free", plan="free")
    assert normalized_plan(user) == "free"
    assert is_premium(user) is False
    assert can_access_pvp(user) is False
    assert can_access_premium_cosmetic(user) is False


def test_premium_user_has_premium_access():
    user = User(steam_id="plan_premium", display_name="Premium", plan="premium")
    assert normalized_plan(user) == "premium"
    assert is_premium(user) is True
    assert can_access_pvp(user) is True
    assert can_access_premium_cosmetic(user) is True


def test_admin_is_treated_as_premium():
    user = User(
        steam_id="plan_admin", display_name="Admin", plan="free", role=UserRole.ADMIN
    )
    assert normalized_plan(user) == "premium"
    assert is_premium(user) is True
    assert can_access_pvp(user) is True
