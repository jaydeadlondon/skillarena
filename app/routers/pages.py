from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.course import Course, Lesson, LessonProgress
from app.models.gamification import Achievement, UserCosmetic
from app.models.pvp import PvpBattle
from app.models.user import User
from app.routers.deps import DbSession, get_current_user, require_user
from app.services.achievements import evaluate_all_achievements
from app.services.quests import get_daily_quest_cards

router = APIRouter(tags=["pages"])


def templates(request: Request):
    return request.app.state.templates


@router.get("/")
async def home(request: Request, current_user: User | None = Depends(get_current_user)):
    return templates(request).TemplateResponse(
        request, "home.html", {"request": request, "user": current_user}
    )


@router.get("/dashboard")
async def dashboard(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    courses_count = await db.scalar(
        select(func.count(Course.id)).where(Course.is_published.is_(True))
    )
    completed_lessons = await db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.completed.is_(True),
        )
    )
    daily_quest_cards = await get_daily_quest_cards(db, user)
    await db.flush()
    battles = (
        (
            await db.execute(
                select(PvpBattle)
                .where(
                    (PvpBattle.challenger_id == user.id)
                    | (PvpBattle.opponent_id == user.id)
                )
                .order_by(PvpBattle.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    study_minutes_2w = await db.scalar(
        select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.updated_at >= datetime.now(UTC) - timedelta(days=14),
        )
    )
    study_minutes_2w = int(study_minutes_2w or 0) // 60
    await db.commit()

    return templates(request).TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "courses_count": courses_count or 0,
            "completed_lessons": completed_lessons or 0,
            "daily_quest_cards": daily_quest_cards[:4],
            "daily_quests_completed": sum(
                1 for card in daily_quest_cards if card["user_quest"].completed
            ),
            "daily_quests_total": len(daily_quest_cards),
            "battles": battles,
            "study_minutes_2w": study_minutes_2w,
            "steam_minutes_2w": user.steam_playtime_2w_minutes,
        },
    )


@router.get("/courses")
async def courses(request: Request, db: DbSession, user: User = Depends(require_user)):
    result = await db.execute(
        select(Course)
        .where(Course.is_published.is_(True))
        .options(selectinload(Course.lessons))
        .order_by(Course.title)
    )
    return templates(request).TemplateResponse(
        request,
        "courses.html",
        {"request": request, "user": user, "courses": result.scalars().all()},
    )


@router.get("/courses/{slug}")
async def course_detail(
    slug: str, request: Request, db: DbSession, user: User = Depends(require_user)
):
    course = (
        await db.execute(
            select(Course)
            .where(Course.slug == slug)
            .options(selectinload(Course.lessons))
        )
    ).scalar_one()
    progress = (
        (
            await db.execute(
                select(LessonProgress).where(LessonProgress.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    progress_by_lesson = {item.lesson_id: item for item in progress}
    return templates(request).TemplateResponse(
        request,
        "course_detail.html",
        {
            "request": request,
            "user": user,
            "course": course,
            "progress_by_lesson": progress_by_lesson,
        },
    )


@router.get("/profile")
async def profile(request: Request, db: DbSession, user: User = Depends(require_user)):
    await evaluate_all_achievements(db, user)
    await db.commit()
    achievements = (
        (
            await db.execute(
                select(Achievement)
                .where(Achievement.users.any(user_id=user.id))
                .order_by(Achievement.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    equipped_cosmetics = (
        (
            await db.execute(
                select(UserCosmetic)
                .where(
                    UserCosmetic.user_id == user.id, UserCosmetic.is_equipped.is_(True)
                )
                .options(selectinload(UserCosmetic.item))
            )
        )
        .scalars()
        .all()
    )
    equipped_by_type = {
        cosmetic.item.item_type: cosmetic.item for cosmetic in equipped_cosmetics
    }
    study_seconds = await db.scalar(
        select(func.coalesce(func.sum(LessonProgress.watched_seconds), 0)).where(
            LessonProgress.user_id == user.id
        )
    )
    return templates(request).TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "achievements": achievements,
            "equipped_by_type": equipped_by_type,
            "study_hours_total": round((study_seconds or 0) / 3600, 1),
        },
    )
