import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models.ai  # noqa: F401,E402
import app.models.analytics  # noqa: F401,E402
import app.models.audit  # noqa: F401,E402
import app.models.course  # noqa: F401,E402
import app.models.gamification  # noqa: F401,E402
import app.models.pvp  # noqa: F401,E402
import app.models.telegram_payment  # noqa: F401,E402
import app.models.user  # noqa: F401,E402
from sqlalchemy import inspect  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


async def main() -> None:
    print("Registered SQLAlchemy tables:")
    for table_name in sorted(Base.metadata.tables.keys()):
        print(f"- {table_name}")

    async with engine.begin() as conn:
        db_tables = await conn.run_sync(
            lambda sync_conn: sorted(inspect(sync_conn).get_table_names())
        )

    print("\nExisting PostgreSQL tables:")
    for table_name in db_tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    asyncio.run(main())
