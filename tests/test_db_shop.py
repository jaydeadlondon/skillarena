import asyncio

from sqlalchemy import select

from app.models.gamification import CosmeticItem, UserCosmetic
from app.models.user import User
from tests.db_helpers import run_with_test_db


def test_user_can_buy_cosmetic_with_skill_points():
    async def scenario(session):
        user = User(steam_id="steam_shop", display_name="Shop Tester", skill_points=100)
        item = CosmeticItem(
            code="test_frame",
            name="Test Frame",
            item_type="profile_frame",
            price_points=40,
            preview_value="#f7c948",
            is_active=True,
        )
        session.add_all([user, item])
        await session.flush()

        user.skill_points -= item.price_points
        session.add(UserCosmetic(user_id=user.id, cosmetic_item_id=item.id))
        await session.commit()
        await session.refresh(user)

        owned = await session.scalar(
            select(UserCosmetic).where(
                UserCosmetic.user_id == user.id,
                UserCosmetic.cosmetic_item_id == item.id,
            )
        )
        assert user.skill_points == 60
        assert owned is not None

    asyncio.run(run_with_test_db(scenario))
