from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.onboarding import get_user_onboarding, save_onboarding

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def onboarding_page(request: Request, db: DbSession, user: User = Depends(require_user)):
    onboarding = await get_user_onboarding(db, user)
    return templates(request).TemplateResponse(
        request,
        "onboarding.html",
        {"request": request, "user": user, "onboarding": onboarding},
    )


@router.post("")
async def complete_onboarding(
    db: DbSession,
    user: User = Depends(require_user),
    learning_goal: str = Form(...),
    experience_level: str = Form("beginner"),
    weekly_goal_minutes: int = Form(120),
    preferred_session_minutes: int = Form(25),
):
    await save_onboarding(
        db,
        user,
        learning_goal,
        experience_level,
        weekly_goal_minutes,
        preferred_session_minutes,
    )
    await db.commit()
    return RedirectResponse("/dashboard?onboarding=completed", status_code=303)
