from fastapi import APIRouter, Depends, Request

from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.achievements import get_achievement_gallery

router = APIRouter(prefix="/achievements", tags=["achievements"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def achievements_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    gallery = await get_achievement_gallery(db, user)
    await db.commit()
    return templates(request).TemplateResponse(
        request,
        "achievements.html",
        {"request": request, "user": user, "gallery": gallery},
    )
