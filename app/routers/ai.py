from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.course import Lesson
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.llm import (
    LLMServiceError,
    ask_lesson_companion,
    get_llm_config,
    recent_lesson_interactions,
    user_llm_requests_today,
)
from app.core.config import get_settings

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
