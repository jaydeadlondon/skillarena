from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AdminAuditLog
from app.models.user import User


async def log_admin_action(
    db: AsyncSession,
    admin: User,
    action: str,
    target_type: str,
    target_id: int | None = None,
    details: str = "",
) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            action=action[:80],
            target_type=target_type[:80],
            target_id=target_id,
            details=details[:4000],
        )
    )
