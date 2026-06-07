import asyncio

from sqlalchemy import select

from app.models.audit import AdminAuditLog
from app.models.user import User
from app.services.audit import log_admin_action
from tests.db_helpers import run_with_test_db


def test_log_admin_action_creates_audit_record():
    async def scenario(session):
        admin = User(steam_id="steam_audit_admin", display_name="Audit Admin")
        session.add(admin)
        await session.flush()

        await log_admin_action(
            session,
            admin,
            "course.update",
            "course",
            42,
            "Updated test course",
        )
        await session.commit()

        log = await session.scalar(
            select(AdminAuditLog).where(AdminAuditLog.admin_user_id == admin.id)
        )
        assert log is not None
        assert log.action == "course.update"
        assert log.target_type == "course"
        assert log.target_id == 42
        assert log.details == "Updated test course"

    asyncio.run(run_with_test_db(scenario))
