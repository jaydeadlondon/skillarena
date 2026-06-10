import asyncio

from app.models.telegram_payment import TelegramPayment
from app.models.user import User
from app.services.telegram_bot import process_telegram_update
from tests.db_helpers import run_with_test_db


def test_telegram_start_with_unknown_payload_is_handled(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id: int, text: str):
        sent_messages.append((chat_id, text))

    monkeypatch.setattr("app.services.telegram_bot.send_message", fake_send_message)

    async def scenario(session):
        result = await process_telegram_update(
            session,
            {
                "message": {
                    "text": "/start premium_missing",
                    "chat": {"id": 123},
                    "from": {"id": 777},
                }
            },
        )
        assert result["action"] == "payment_not_found"
        assert sent_messages

    asyncio.run(run_with_test_db(scenario))


def test_telegram_successful_payment_activates_premium(monkeypatch):
    sent_messages = []

    async def fake_send_message(chat_id: int, text: str):
        sent_messages.append((chat_id, text))

    monkeypatch.setattr("app.services.telegram_bot.send_message", fake_send_message)

    async def scenario(session):
        user = User(steam_id="tg_bot_paid", display_name="TG Paid", plan="free")
        session.add(user)
        await session.flush()
        payment = TelegramPayment(
            user_id=user.id,
            payload="premium_test_payload",
            plan_code="1m",
            premium_days=30,
            stars_amount=99,
        )
        session.add(payment)
        await session.flush()

        result = await process_telegram_update(
            session,
            {
                "message": {
                    "chat": {"id": 123},
                    "from": {"id": 777},
                    "successful_payment": {
                        "invoice_payload": "premium_test_payload",
                        "telegram_payment_charge_id": "charge",
                        "currency": "XTR",
                        "total_amount": 99,
                    },
                }
            },
        )
        await session.commit()
        await session.refresh(user)
        assert result["action"] == "payment_activated"
        assert user.plan == "premium"
        assert user.premium_until is not None
        assert sent_messages

    asyncio.run(run_with_test_db(scenario))
