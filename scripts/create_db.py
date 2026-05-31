import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models.course  # noqa: F401,E402
import app.models.gamification  # noqa: F401,E402
import app.models.pvp  # noqa: F401,E402
import app.models.user  # noqa: F401,E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


async def main() -> None:
    table_names = sorted(Base.metadata.tables.keys())
    if not table_names:
        raise RuntimeError(
            "No SQLAlchemy tables were registered. Model imports failed."
        )

    print(f"Registered tables: {', '.join(table_names)}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")


if __name__ == "__main__":
    asyncio.run(main())
