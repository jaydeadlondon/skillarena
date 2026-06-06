from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.core.validation import ValidationError, clamp_int, clean_text, validate_choice
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.onboarding import get_user_onboarding, save_onboarding

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def onboarding_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
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
    daily_goal_minutes: int = Form(20),
    preferred_session_minutes: int = Form(25),
    preferred_learning_style: str = Form("video"),
    focus_challenge: str = Form("distractions"),
    wants_pvp: bool = Form(False),
    wants_steam_balance: bool = Form(False),
):
    try:
        learning_goal = clean_text(
            learning_goal, max_length=120, field_name="learning goal"
        )
        experience_level = validate_choice(
            experience_level,
            allowed={"beginner", "intermediate", "advanced"},
            field_name="experience level",
        )
        weekly_goal_minutes = clamp_int(
            weekly_goal_minutes, min_value=30, max_value=2000, field_name="weekly goal"
        )
        daily_goal_minutes = clamp_int(
            daily_goal_minutes, min_value=5, max_value=240, field_name="daily goal"
        )
        preferred_session_minutes = clamp_int(
            preferred_session_minutes,
            min_value=5,
            max_value=120,
            field_name="focus session",
        )
        preferred_learning_style = validate_choice(
            preferred_learning_style,
            allowed={"video", "reading", "practice", "mixed"},
            field_name="learning style",
        )
        focus_challenge = validate_choice(
            focus_challenge,
            allowed={
                "distractions",
                "procrastination",
                "overwhelm",
                "consistency",
                "time_management",
            },
            field_name="focus challenge",
        )
    except ValidationError:
        return RedirectResponse("/onboarding?error=validation", status_code=303)

    await save_onboarding(
        db,
        user,
        learning_goal,
        experience_level,
        weekly_goal_minutes,
        preferred_session_minutes,
        daily_goal_minutes,
        preferred_learning_style,
        focus_challenge,
        wants_pvp,
        wants_steam_balance,
    )
    await db.commit()
    return RedirectResponse("/dashboard?onboarding=completed", status_code=303)
