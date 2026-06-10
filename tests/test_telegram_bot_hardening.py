import asyncio

from app.models.telegram_payment import TelegramPayment
from app.models.user import User
from app.services.telegram_bot import process_telegram_update
from tests.db_helpers import run_with_test_db


def test_pre_checkout_rejects_amount_mismatch(monkeypatch):
    answers = []

    async def fake_answer(
        pre_checkout_query_id: str, ok: bool, error_message: str | None = None
    ):
        answers.append((pre_checkout_query_id, ok, error_message))

    monkeypatch.setattr(
        "app.services.telegram_bot.answer_pre_checkout_query", fake_answer
    )

    async def scenario(session):
        user = User(steam_id="tg_precheck", display_name="TG Precheck")
        session.add(user)
        await session.flush()
        session.add(
            TelegramPayment(
                user_id=user.id,
                payload="premium_precheck",
                plan_code="1m",
                premium_days=30,
                stars_amount=99,
            )
        )
        await session.flush()

        result = await process_telegram_update(
            session,
            {
                "pre_checkout_query": {
                    "id": "pcq",
                    "invoice_payload": "premium_precheck",
                    "currency": "XTR",
                    "total_amount": 1,
                }
            },
        )
        assert result["action"] == "pre_checkout_amount_mismatch"
        assert answers == [("pcq", False, "Payment amount mismatch.")]

    asyncio.run(run_with_test_db(scenario))


def test_duplicate_successful_payment_does_not_extend_twice(monkeypatch):
    sent = []

    async def fake_send_message(chat_id: int, text: str):
        sent.append(text)

    monkeypatch.setattr("app.services.telegram_bot.send_message", fake_send_message)

    async def scenario(session):
        user = User(steam_id="tg_duplicate", display_name="TG Duplicate", plan="free")
        session.add(user)
        await session.flush()
        payment = TelegramPayment(
            user_id=user.id,
            payload="premium_duplicate",
            plan_code="1m",
            premium_days=30,
            stars_amount=99,
        )
        session.add(payment)
        await session.flush()
        update = {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 777},
                "successful_payment": {
                    "invoice_payload": "premium_duplicate",
                    "currency": "XTR",
                    "total_amount": 99,
                },
            }
        }

        first = await process_telegram_update(session, update)
        first_until = user.premium_until
        second = await process_telegram_update(session, update)
        second_until = user.premium_until

        assert first["action"] == "payment_activated"
        assert second["action"] == "payment_already_processed"
        assert first_until == second_until

    asyncio.run(run_with_test_db(scenario))
