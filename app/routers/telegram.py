from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.analytics import track_event
from app.services.telegram_bot import process_telegram_update
from app.services.telegram_payments import create_telegram_payment, telegram_deep_link

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
            return {"ok": False, "error": "bad secret"}

    update = await request.json()
    result = await process_telegram_update(db, update)
    await db.commit()
    return result
