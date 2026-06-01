from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import UserNotification
from app.models.user import User


async def create_notification(
    db: AsyncSession,
    user: User,
    title: str,
    message: str,
    notification_type: str = "system",
) -> UserNotification:
    notification = UserNotification(
        user_id=user.id,
        title=title[:160],
        message=message,
        notification_type=notification_type[:40],
    )
    db.add(notification)
    return notification


async def unread_notifications_count(db: AsyncSession, user: User) -> int:
    count = await db.scalar(
        select(func.count(UserNotification.id)).where(
            UserNotification.user_id == user.id,
            UserNotification.is_read.is_(False),
        )
    )
    return int(count or 0)


async def list_user_notifications(
    db: AsyncSession, user: User, limit: int = 50
) -> list[UserNotification]:
    return (
        (
            await db.execute(
                select(UserNotification)
                .where(UserNotification.user_id == user.id)
                .order_by(UserNotification.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


async def mark_all_notifications_read(db: AsyncSession, user: User) -> None:
    notifications = (
        (
            await db.execute(
                select(UserNotification).where(
                    UserNotification.user_id == user.id,
                    UserNotification.is_read.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    for notification in notifications:
        notification.is_read = True


async def mark_notification_read(
    db: AsyncSession, user: User, notification_id: int
) -> bool:
    notification = await db.scalar(
        select(UserNotification).where(
            UserNotification.id == notification_id,
            UserNotification.user_id == user.id,
        )
    )
    if notification is None:
        return False
    notification.is_read = True
    return True
