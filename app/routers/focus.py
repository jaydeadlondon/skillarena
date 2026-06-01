from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.models.gamification import FocusSession
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.activity import add_activity_seconds
from app.services.rewards import add_skill_points
from app.services.streaks import sync_user_streak

router = APIRouter(prefix="/focus", tags=["focus"])

ALLOWED_DURATIONS = {5, 15, 25, 50}


def templates(request: Request):
    return request.app.state.templates


def focus_reward(duration_minutes: int) -> int:
    return max(5, duration_minutes // 5 * 5)


@router.get("")
async def focus_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    completed_today = await db.scalar(
        select(func.count(FocusSession.id)).where(
            FocusSession.user_id == user.id,
            FocusSession.completed.is_(True),
            func.date(FocusSession.created_at) == func.current_date(),
        )
    )
    total_today_minutes = await db.scalar(
        select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
            FocusSession.user_id == user.id,
            FocusSession.completed.is_(True),
            func.date(FocusSession.created_at) == func.current_date(),
        )
    )
    recent_sessions = (
        (
            await db.execute(
                select(FocusSession)
                .where(FocusSession.user_id == user.id)
                .order_by(FocusSession.created_at.desc())
                .limit(8)
            )
        )
        .scalars()
        .all()
    )
    return templates(request).TemplateResponse(
        request,
        "focus.html",
        {
            "request": request,
            "user": user,
            "durations": sorted(ALLOWED_DURATIONS),
            "completed_today": completed_today or 0,
            "total_today_minutes": total_today_minutes or 0,
            "recent_sessions": recent_sessions,
        },
    )


@router.post("/complete")
async def complete_focus_session(
    db: DbSession,
    user: User = Depends(require_user),
    duration_minutes: int = Form(...),
):
    if duration_minutes not in ALLOWED_DURATIONS:
        return RedirectResponse("/focus?error=invalid-duration", status_code=303)

    reward = focus_reward(duration_minutes)
    session = FocusSession(
        user_id=user.id,
        duration_minutes=duration_minutes,
        reward_points=reward,
        completed=True,
    )
    db.add(session)
    await add_activity_seconds(db, user, "focus", duration_minutes * 60)
    await add_activity_seconds(db, user, "site", duration_minutes * 60)
    await add_skill_points(
        db, user, reward, "Focus session completed", "focus_session", None
    )
    await sync_user_streak(db, user)
    await db.commit()
    return RedirectResponse(
        f"/focus?success=completed&reward={reward}", status_code=303
    )
