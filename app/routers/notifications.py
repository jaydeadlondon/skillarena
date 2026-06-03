from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.notifications import (
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    unread_notifications_count,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def notifications_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    notifications = await list_user_notifications(db, user)
    unread_count = await unread_notifications_count(db, user)
    return templates(request).TemplateResponse(
        request,
        "notifications.html",
        {
            "request": request,
            "user": user,
            "notifications": notifications,
            "unread_count": unread_count,
        },
    )


@router.post("/read-all")
async def read_all_notifications(db: DbSession, user: User = Depends(require_user)):
    await mark_all_notifications_read(db, user)
    await db.commit()
    return RedirectResponse("/notifications?success=read-all", status_code=303)


@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: int, db: DbSession, user: User = Depends(require_user)
):
    await mark_notification_read(db, user, notification_id)
    await db.commit()
    return RedirectResponse("/notifications", status_code=303)
