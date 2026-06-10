from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import get_settings
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.analytics import track_event
from app.services.telegram_payments import (
    activate_telegram_payment,
    answer_pre_checkout_query,
    create_telegram_payment,
    find_payment_by_payload,
    send_stars_invoice,
    telegram_deep_link,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/premium/start/{plan_code}")
async def start_telegram_premium_payment(
    plan_code: str, db: DbSession, user: User = Depends(require_user)
):
    payment = await create_telegram_payment(db, user, plan_code)
    await track_event(
        db,
        user,
        "telegram_payment_created",
        "telegram_payment",
        payment.id,
        {"plan": plan_code, "stars": payment.stars_amount},
    )
    await db.commit()
    return RedirectResponse(telegram_deep_link(payment), status_code=303)


@router.post("/webhook")
async def telegram_webhook(request: Request, db: DbSession):
    settings = get_settings()
    if settings.telegram_webhook_secret:
        supplied = request.headers.get("x-telegram-bot-api-secret-token")
        if supplied != settings.telegram_webhook_secret:
            return JSONResponse({"ok": False, "error": "bad secret"}, status_code=403)

    update = await request.json()

    message = update.get("message") or {}
    text = message.get("text") or ""
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}

    if text.startswith("/start premium_"):
        payload = text.split(maxsplit=1)[1].strip()
        payment = await find_payment_by_payload(db, payload)
        if payment is None:
            return {"ok": True}
        payment.telegram_user_id = from_user.get("id")
        await db.commit()
        await send_stars_invoice(payment, chat.get("id"))
        return {"ok": True}

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
            return {"ok": True}
        await answer_pre_checkout_query(pre_checkout.get("id"), True)
        return {"ok": True}

    successful_payment = message.get("successful_payment")
    if successful_payment:
        payload = successful_payment.get("invoice_payload", "")
        payment = await find_payment_by_payload(db, payload)
        if payment is None:
            return {"ok": True}
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
        await db.commit()
        return {"ok": True}

    return {"ok": True}
