import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/grant_admin.py <steam_id_64>")
        print("Existing users:")
        async with AsyncSessionLocal() as db:
            users = (
                (await db.execute(select(User).order_by(User.created_at.desc())))
                .scalars()
                .all()
            )
            for user in users:
                print(f"- {user.steam_id} | {user.display_name} | {user.role.value}")
        return

    steam_id = sys.argv[1].strip()
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.steam_id == steam_id))
        if user is None:
            print(
                f"User with SteamID {steam_id} was not found. Log in with Steam first."
            )
            return
        user.role = UserRole.ADMIN
        await db.commit()
        print(f"Granted admin role to {user.display_name} ({user.steam_id}).")


if __name__ == "__main__":
    asyncio.run(main())
