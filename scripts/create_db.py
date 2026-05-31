import asyncio

from app.db.base import Base
from app.db.session import engine
from app import models


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")


if __name__ == "__main__":
    asyncio.run(main())
