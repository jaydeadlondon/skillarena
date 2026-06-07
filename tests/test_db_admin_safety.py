import asyncio

from sqlalchemy import select

from app.models.audit import AdminAuditLog
from app.models.user import User, UserRole
from app.routers.admin import update_user_role
from tests.db_helpers import run_with_test_db


def test_cannot_demote_last_admin():
    async def scenario(session):
        admin = User(
            steam_id="steam_last_admin",
            display_name="Last Admin",
            role=UserRole.ADMIN,
        )
        session.add(admin)
        await session.flush()

        response = await update_user_role(admin.id, session, admin, role="user")
        await session.commit()
        await session.refresh(admin)

        assert response.status_code == 303
        assert "cannot-demote-yourself" in response.headers["location"]
        assert admin.role == UserRole.ADMIN

    asyncio.run(run_with_test_db(scenario))


def test_admin_can_promote_user_and_audit_is_logged():
    async def scenario(session):
        admin = User(
            steam_id="steam_promoter_admin",
            display_name="Promoter Admin",
            role=UserRole.ADMIN,
        )
        target = User(
            steam_id="steam_promoted_user",
            display_name="Promoted User",
            role=UserRole.USER,
        )
        session.add_all([admin, target])
        await session.flush()

        response = await update_user_role(target.id, session, admin, role="admin")
        await session.commit()
        await session.refresh(target)

        audit_log = await session.scalar(
            select(AdminAuditLog).where(
                AdminAuditLog.action == "user.role.update",
                AdminAuditLog.target_id == target.id,
            )
        )

        assert response.status_code == 303
        assert target.role == UserRole.ADMIN
        assert audit_log is not None
        assert "user -> admin" in audit_log.details

    asyncio.run(run_with_test_db(scenario))
