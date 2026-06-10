import asyncio
from datetime import UTC, datetime

from app.models.user import User
from app.services.plans import is_premium
from app.services.telegram_payments import (
    create_telegram_payment,
    extend_premium,
    telegram_plan_options,
)
from tests.db_helpers import run_with_test_db


def test_telegram_plan_options_prices():
    options = telegram_plan_options()
    assert options["1m"]["stars"] == 99
    assert options["3m"]["stars"] == 299
    assert options["6m"]["stars"] == 419
    assert options["12m"]["stars"] == 600


def test_extend_premium_sets_until_and_plan():
    user = User(steam_id="tg_extend", display_name="TG Extend", plan="free")
    extend_premium(user, 30)
    assert user.plan == "premium"
    assert user.premium_until is not None
    assert user.premium_until > datetime.now(UTC)
    assert is_premium(user) is True


def test_create_telegram_payment():
    async def scenario(session):
        user = User(steam_id="tg_payment", display_name="TG Payment", plan="free")
        session.add(user)
        await session.flush()

        payment = await create_telegram_payment(session, user, "3m")
        await session.commit()

        assert payment.user_id == user.id
        assert payment.plan_code == "3m"
        assert payment.premium_days == 90
        assert payment.stars_amount == 299
        assert payment.status == "pending"
        assert payment.payload.startswith("premium_")

    asyncio.run(run_with_test_db(scenario))
