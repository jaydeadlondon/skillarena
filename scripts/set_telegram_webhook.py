import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not configured.")
        raise SystemExit(1)
    if not settings.app_base_url.startswith("https://"):
        print("APP_BASE_URL must be public HTTPS for Telegram webhooks.")
        raise SystemExit(1)

    webhook_url = f"{settings.app_base_url.rstrip('/')}/telegram/webhook"
    payload = {"url": webhook_url}
    if settings.telegram_webhook_secret:
        payload["secret_token"] = settings.telegram_webhook_secret

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
            json=payload,
        )
    print(response.status_code)
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    asyncio.run(main())
