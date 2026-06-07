import asyncio

from sqlalchemy import select

from app.models.gamification import UserNotification
from app.models.user import CurrencyTransaction, User
from app.services.rewards import add_skill_points
from tests.db_helpers import run_with_test_db


def test_add_skill_points_creates_transaction_and_notification():
    async def scenario(session):
        user = User(
            steam_id="steam_rewards", display_name="Reward Tester", skill_points=0
        )
        session.add(user)
        await session.flush()

        await add_skill_points(session, user, 50, "Test reward", "test", 1)
        await session.commit()
        await session.refresh(user)

        transaction = await session.scalar(
            select(CurrencyTransaction).where(CurrencyTransaction.user_id == user.id)
        )
        notification = await session.scalar(
            select(UserNotification).where(UserNotification.user_id == user.id)
        )

        assert user.skill_points == 50
        assert transaction is not None
        assert transaction.amount == 50
        assert transaction.reason == "Test reward"
        assert notification is not None
        assert notification.title == "+50 Skill Points"
        assert notification.notification_type == "reward"

    asyncio.run(run_with_test_db(scenario))
