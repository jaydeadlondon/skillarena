import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.telegram_payment import TelegramPayment
from app.models.user import User

PAYMENT_PENDING = "pending"
PAYMENT_SUCCEEDED = "succeeded"
PAYMENT_FAILED = "failed"

PLAN_LABELS = {
    "1m": "1 month",
    "3m": "3 months",
    "6m": "6 months",
    "12m": "1 year",
}


def telegram_plan_options() -> dict[str, dict[str, int | str]]:
    settings = get_settings()
    return {
        "1m": {
            "label": "1 month",
            "days": settings.telegram_premium_days_1m,
            "stars": settings.telegram_stars_price_1m,
        },
        "3m": {
            "label": "3 months",
            "days": settings.telegram_premium_days_3m,
            "stars": settings.telegram_stars_price_3m,
        },
        "6m": {
            "label": "6 months",
            "days": settings.telegram_premium_days_6m,
            "stars": settings.telegram_stars_price_6m,
        },
        "12m": {
            "label": "1 year",
            "days": settings.telegram_premium_days_12m,
            "stars": settings.telegram_stars_price_12m,
        },
    }


def extend_premium(user: User, days: int) -> None:
    now = datetime.now(UTC)
    current = user.premium_until
    if current and current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    base = current if current and current > now else now
    user.premium_until = base + timedelta(days=days)
    user.plan = "premium"


async def create_telegram_payment(
    db: AsyncSession, user: User, plan_code: str
) -> TelegramPayment:
    options = telegram_plan_options()
    if plan_code not in options:
        plan_code = "1m"
    option = options[plan_code]
    payment = TelegramPayment(
        user_id=user.id,
        payload=f"premium_{secrets.token_urlsafe(24)}",
        status=PAYMENT_PENDING,
        plan_code=plan_code,
        premium_days=int(option["days"]),
        stars_amount=int(option["stars"]),
    )
    db.add(payment)
    await db.flush()
    return payment


def telegram_deep_link(payment: TelegramPayment) -> str:
    settings = get_settings()
    username = settings.telegram_bot_username.strip().lstrip("@")
    if not username:
        return "/premium?error=telegram-bot-not-configured"
    return f"https://t.me/{username}?start={payment.payload}"


async def find_payment_by_payload(
    db: AsyncSession, payload: str
) -> TelegramPayment | None:
    return await db.scalar(
        select(TelegramPayment).where(TelegramPayment.payload == payload)
    )


async def telegram_api(method: str, data: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("Telegram bot token is not configured")
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=data)
    response.raise_for_status()
    return response.json()


async def send_stars_invoice(payment: TelegramPayment, chat_id: int) -> None:
    label = PLAN_LABELS.get(payment.plan_code, payment.plan_code)
    await telegram_api(
        "sendInvoice",
        {
            "chat_id": chat_id,
            "title": f"SkillArena Premium · {label}",
            "description": f"Premium access for {payment.premium_days} days.",
            "payload": payment.payload,
            "currency": "XTR",
            "prices": [{"label": f"Premium {label}", "amount": payment.stars_amount}],
            "provider_token": "",
        },
    )


async def answer_pre_checkout_query(
    pre_checkout_query_id: str, ok: bool, error_message: str | None = None
) -> None:
    payload: dict[str, Any] = {"pre_checkout_query_id": pre_checkout_query_id, "ok": ok}
    if error_message:
        payload["error_message"] = error_message
    await telegram_api("answerPreCheckoutQuery", payload)


async def activate_telegram_payment(
    db: AsyncSession,
    payment: TelegramPayment,
    telegram_user_id: int | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> None:
    if payment.status == PAYMENT_SUCCEEDED:
        return
    user = await db.get(User, payment.user_id)
    if user is None:
        payment.status = PAYMENT_FAILED
        payment.raw_payload = json.dumps(raw_payload or {}, ensure_ascii=False)[:4000]
        return
    payment.status = PAYMENT_SUCCEEDED
    payment.telegram_user_id = telegram_user_id or payment.telegram_user_id
    payment.paid_at = datetime.now(UTC)
    payment.raw_payload = json.dumps(raw_payload or {}, ensure_ascii=False)[:4000]
    extend_premium(user, payment.premium_days)
