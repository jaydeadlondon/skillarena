import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services.telegram_bot import process_telegram_update  # noqa: E402


async def get_updates(
    client: httpx.AsyncClient, token: str, offset: int | None
) -> list[dict]:
    payload = {"timeout": 30, "allowed_updates": ["message", "pre_checkout_query"]}
    if offset is not None:
        payload["offset"] = offset
    response = await client.post(
        f"https://api.telegram.org/bot{token}/getUpdates", json=payload, timeout=40
    )
    response.raise_for_status()
    data = response.json()
    return data.get("result", [])


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not configured.")
        raise SystemExit(1)

    print("SkillArena Telegram bot polling started. Press Ctrl+C to stop.")
    offset: int | None = None
    async with httpx.AsyncClient() as client:
        while True:
            updates = await get_updates(client, settings.telegram_bot_token, offset)
            for update in updates:
                offset = int(update["update_id"]) + 1
                async with AsyncSessionLocal() as db:
                    try:
                        result = await process_telegram_update(db, update)
                        await db.commit()
                        print(result)
                    except Exception as exc:
                        await db.rollback()
                        print(f"Telegram update failed: {exc}")
            await asyncio.sleep(0.2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Telegram bot polling stopped.")
