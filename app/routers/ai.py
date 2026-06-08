from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.course import Lesson, LessonProgress
from app.models.gamification import FocusSession, UserOnboarding
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.activity import get_activity_summary
from app.services.analytics import track_event
from app.services.course_progress import find_continue_lesson
from app.services.llm import (
    LLMServiceError,
    ask_dashboard_planner,
    ask_lesson_companion,
    delete_lesson_interactions,
    get_llm_config,
    recent_lesson_interactions,
    user_llm_requests_today,
)
from app.services.quests import get_daily_quest_cards, get_weekly_quest_cards

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/config")
async def ai_config(user: User = Depends(require_user)):
    settings = get_settings()
    provider, base_url, model = get_llm_config()
    return {
        "enabled": settings.llm_enabled,
        "provider": provider,
        "base_url": base_url,
        "chat_completions_endpoint": f"{base_url}/chat/completions",
        "model": model,
        "daily_limit_per_user": settings.llm_daily_limit_per_user,
        "api_key_configured": bool(
            settings.llm_api_key and not settings.llm_api_key.startswith("put-")
        ),
    }


async def build_dashboard_ai_summary(db: DbSession, user: User) -> dict:
    onboarding = await db.scalar(
        select(UserOnboarding).where(UserOnboarding.user_id == user.id)
    )
    activity_summary = await get_activity_summary(db, user)
    continue_course, continue_lesson, _ = await find_continue_lesson(db, user)
    daily_cards = await get_daily_quest_cards(db, user)
    weekly_cards = await get_weekly_quest_cards(db, user)
    focus_minutes_today = await db.scalar(
        select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
            FocusSession.user_id == user.id,
            FocusSession.completed.is_(True),
            func.date(FocusSession.created_at) == func.current_date(),
        )
    )
    study_minutes_2w = await db.scalar(
        select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.updated_at >= datetime.now(UTC) - timedelta(days=14),
        )
    )
    return {
        "learning_goal": (
            onboarding.learning_goal
            if onboarding
            else "Build a consistent learning habit"
        ),
        "experience_level": onboarding.experience_level if onboarding else "beginner",
        "daily_goal_minutes": onboarding.daily_goal_minutes if onboarding else 20,
        "focus_challenge": onboarding.focus_challenge if onboarding else "consistency",
        "preferred_session_minutes": (
            onboarding.preferred_session_minutes if onboarding else 25
        ),
        "focus_minutes_today": int(focus_minutes_today or 0),
        "lesson_minutes_today": int(activity_summary.get("lesson_seconds", 0)) // 60,
        "current_streak_days": user.current_streak_days,
        "next_lesson_title": continue_lesson.title if continue_lesson else "None",
        "next_course_title": continue_course.title if continue_course else "None",
        "daily_quests_completed": sum(
            1 for card in daily_cards if card["user_quest"].completed
        ),
        "daily_quests_total": len(daily_cards),
        "weekly_quests_completed": sum(
            1 for card in weekly_cards if card["user_quest"].completed
        ),
        "weekly_quests_total": len(weekly_cards),
        "claimable_quests": sum(
            1 for card in daily_cards + weekly_cards if card["can_claim"]
        ),
        "steam_minutes_2w": user.steam_playtime_2w_minutes,
        "study_minutes_2w": int(study_minutes_2w or 0) // 60,
    }


@router.post("/dashboard/plan")
async def dashboard_ai_plan(db: DbSession, user: User = Depends(require_user)):
    try:
        summary = await build_dashboard_ai_summary(db, user)
        interaction = await ask_dashboard_planner(db, user, summary)
        await track_event(
            db,
            user,
            "ai_request",
            "dashboard",
            None,
            {"prompt_type": "dashboard_planner"},
        )
        await db.commit()
        await db.refresh(interaction)
        return {
            "ok": True,
            "response": interaction.response,
            "prompt_type": interaction.prompt_type,
            "created_at": interaction.created_at.isoformat(),
        }
    except LLMServiceError as exc:
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc),
                "fallback": "Action: Continue your next lesson\nWhy: It is the simplest way to protect your streak and make visible progress today.",
            },
            status_code=400,
        )


@router.get("/lessons/{lesson_id}/history")
async def lesson_ai_history(
    lesson_id: int, db: DbSession, user: User = Depends(require_user)
):
    interactions = await recent_lesson_interactions(db, user, lesson_id)
    settings = get_settings()
    used = await user_llm_requests_today(db, user)
    return {
        "enabled": settings.llm_enabled,
        "used_today": used,
        "daily_limit": settings.llm_daily_limit_per_user,
        "items": [
            {
                "id": item.id,
                "prompt_type": item.prompt_type,
                "response": item.response,
                "provider": item.provider,
                "model": item.model,
                "created_at": item.created_at.isoformat(),
            }
            for item in interactions
        ],
    }


@router.delete("/lessons/{lesson_id}/history")
async def clear_lesson_ai_history(
    lesson_id: int, db: DbSession, user: User = Depends(require_user)
):
    deleted_count = await delete_lesson_interactions(db, user, lesson_id)
    await db.commit()
    return {"ok": True, "deleted_count": deleted_count}


@router.post("/lessons/{lesson_id}/ask")
async def ask_lesson_ai(
    lesson_id: int,
    db: DbSession,
    user: User = Depends(require_user),
    action: str = Form("explain"),
    custom_prompt: str = Form(""),
):
    lesson = (
        await db.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.course))
        )
    ).scalar_one_or_none()
    if lesson is None:
        return JSONResponse(
            {"ok": False, "error": "Lesson not found."}, status_code=404
        )
    try:
        interaction = await ask_lesson_companion(
            db,
            user,
            lesson,
            action,
            custom_prompt.strip() or None,
        )
        await track_event(
            db, user, "ai_request", "lesson", lesson.id, {"prompt_type": action}
        )
        await db.commit()
        await db.refresh(interaction)
        return {
            "ok": True,
            "response": interaction.response,
            "prompt_type": interaction.prompt_type,
            "provider": interaction.provider,
            "model": interaction.model,
            "created_at": interaction.created_at.isoformat(),
        }
    except LLMServiceError as exc:
        return JSONResponse(
            {
                "ok": False,
                "error": str(exc),
                "fallback": "AI is unavailable right now. Try summarizing the lesson into one tiny next step: watch, pause, write one note, then continue.",
            },
            status_code=400,
        )
