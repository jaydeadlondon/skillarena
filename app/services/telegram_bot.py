from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.analytics import track_event
from app.services.telegram_payments import (
    activate_telegram_payment,
    answer_pre_checkout_query,
    find_payment_by_payload,
    send_stars_invoice,
    telegram_api,
)


async def send_message(chat_id: int, text: str) -> None:
    await telegram_api("sendMessage", {"chat_id": chat_id, "text": text})


async def process_telegram_update(db: AsyncSession, update: dict) -> dict:
    message = update.get("message") or {}
    text = message.get("text") or ""
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    from_user = message.get("from") or {}

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        if payload.startswith("premium_"):
            payment = await find_payment_by_payload(db, payload)
            if payment is None:
                if chat_id:
                    await send_message(
                        chat_id,
                        "Payment link was not found or expired. Open Premium page and try again.",
                    )
                return {"ok": True, "action": "payment_not_found"}
            payment.telegram_user_id = from_user.get("id")
            await send_stars_invoice(payment, chat_id)
            return {"ok": True, "action": "invoice_sent", "payment_id": payment.id}

        if chat_id:
            await send_message(
                chat_id,
                "Welcome to SkillArena. Open the Premium page on the website and choose a Telegram Stars plan to continue.",
            )
        return {"ok": True, "action": "start_help"}

    if text.startswith("/premium"):
        if chat_id:
            await send_message(
                chat_id,
                "Premium is purchased from the SkillArena website. Open /premium and choose a Stars plan.",
            )
        return {"ok": True, "action": "premium_help"}

    pre_checkout = update.get("pre_checkout_query")
    if pre_checkout:
        payload = pre_checkout.get("invoice_payload", "")
        payment = await find_payment_by_payload(db, payload)
        if payment is None or payment.status != "pending":
            await answer_pre_checkout_query(
                pre_checkout.get("id"),
                False,
                "Payment was not found or already processed.",
            )
            return {"ok": True, "action": "pre_checkout_rejected"}
        await answer_pre_checkout_query(pre_checkout.get("id"), True)
        return {"ok": True, "action": "pre_checkout_ok", "payment_id": payment.id}

    successful_payment = message.get("successful_payment")
    if successful_payment:
        payload = successful_payment.get("invoice_payload", "")
        payment = await find_payment_by_payload(db, payload)
        if payment is None:
            if chat_id:
                await send_message(
                    chat_id,
                    "Payment was received, but SkillArena could not find the linked order. Contact support.",
                )
            return {"ok": True, "action": "paid_payment_not_found"}
        await activate_telegram_payment(
            db, payment, from_user.get("id"), successful_payment
        )
        user = await db.get(User, payment.user_id)
        await track_event(
            db,
            user,
            "telegram_payment_succeeded",
            "telegram_payment",
            payment.id,
            {"plan": payment.plan_code, "stars": payment.stars_amount},
        )
        if chat_id:
            await send_message(
                chat_id,
                f"Premium activated for {payment.premium_days} days. Thank you for supporting SkillArena!",
            )
        return {"ok": True, "action": "payment_activated", "payment_id": payment.id}

    return {"ok": True, "action": "ignored"}
