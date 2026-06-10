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
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/deleteWebhook",
            json={"drop_pending_updates": True},
        )
    print(response.status_code)
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    asyncio.run(main())
