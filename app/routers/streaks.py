from fastapi import APIRouter, Depends, Request

from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.streaks import (
    MIN_STUDY_SECONDS_FOR_STREAK,
    get_streak_timeline,
    sync_user_streak,
)

router = APIRouter(prefix="/streaks", tags=["streaks"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def streaks_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    await sync_user_streak(db, user)
    await db.commit()
    timeline = await get_streak_timeline(db, user, days=14)
    return templates(request).TemplateResponse(
        request,
        "streaks.html",
        {
            "request": request,
            "user": user,
            "timeline": timeline,
            "min_study_minutes": MIN_STUDY_SECONDS_FOR_STREAK // 60,
        },
    )
