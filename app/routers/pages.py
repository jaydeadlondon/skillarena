from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.course import Course, LessonProgress
from app.models.gamification import (
    Achievement,
    FocusSession,
    UserAchievement,
    UserActivityDay,
    UserCosmetic,
    UserOnboarding,
)
from app.models.pvp import BattleStatus, PvpBattle
from app.models.user import CurrencyTransaction, User
from app.routers.deps import DbSession, get_current_user, require_user
from app.services.achievements import evaluate_all_achievements
from app.services.activity import get_activity_summary
from app.services.course_progress import find_continue_lesson, get_course_progress
from app.services.onboarding import has_completed_onboarding
from app.services.quests import get_daily_quest_cards, get_weekly_quest_cards
from app.services.streaks import get_streak_timeline, sync_user_streak

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
    if not await has_completed_onboarding(db, user):
        return RedirectResponse("/onboarding", status_code=303)

    courses_count = await db.scalar(
        select(func.count(Course.id)).where(Course.is_published.is_(True))
    )
    completed_lessons = await db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.completed.is_(True),
        )
    )
    await sync_user_streak(db, user)
    streak_timeline = await get_streak_timeline(db, user, days=7)
    activity_summary = await get_activity_summary(db, user)
    continue_course, continue_lesson, continue_progress = await find_continue_lesson(
        db, user
    )
    daily_quest_cards = await get_daily_quest_cards(db, user)
    weekly_quest_cards = await get_weekly_quest_cards(db, user)
    focus_minutes_today = await db.scalar(
        select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
            FocusSession.user_id == user.id,
            FocusSession.completed.is_(True),
            func.date(FocusSession.created_at) == func.current_date(),
        )
    )
    onboarding = await db.scalar(
        select(UserOnboarding).where(UserOnboarding.user_id == user.id)
    )
    recommended_action = "Continue your next lesson"
    recommended_url = (
        f"/learn/lessons/{continue_lesson.id}" if continue_lesson else "/courses"
    )
    if (
        onboarding
        and int(focus_minutes_today or 0) < onboarding.daily_goal_minutes
        and onboarding.preferred_session_minutes <= 25
    ):
        recommended_action = (
            f"Start a {onboarding.preferred_session_minutes}-min focus sprint"
        )
        recommended_url = "/focus"
    elif daily_quest_cards and any(card["can_claim"] for card in daily_quest_cards):
        recommended_action = "Claim your completed quest reward"
        recommended_url = "/quests"
    await db.flush()
    achievements_total = await db.scalar(select(func.count(Achievement.id)))
    achievements_unlocked = await db.scalar(
        select(func.count(UserAchievement.id)).where(UserAchievement.user_id == user.id)
    )
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
            "streak_timeline": streak_timeline,
            "activity_summary": activity_summary,
            "continue_course": continue_course,
            "continue_lesson": continue_lesson,
            "continue_progress": continue_progress,
            "focus_minutes_today": focus_minutes_today or 0,
            "onboarding": onboarding,
            "recommended_action": recommended_action,
            "recommended_url": recommended_url,
            "daily_quest_cards": daily_quest_cards[:4],
            "daily_quests_completed": sum(
                1 for card in daily_quest_cards if card["user_quest"].completed
            ),
            "daily_quests_total": len(daily_quest_cards),
            "weekly_quests_completed": sum(
                1 for card in weekly_quest_cards if card["user_quest"].completed
            ),
            "weekly_quests_total": len(weekly_quest_cards),
            "achievements_total": achievements_total or 0,
            "achievements_unlocked": achievements_unlocked or 0,
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
    courses_list = result.scalars().all()
    course_cards = []
    for course in courses_list:
        course_cards.append(
            {"course": course, "progress": await get_course_progress(db, user, course)}
        )
    return templates(request).TemplateResponse(
        request,
        "courses.html",
        {"request": request, "user": user, "course_cards": course_cards},
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
    progress = await get_course_progress(db, user, course)
    return templates(request).TemplateResponse(
        request,
        "course_detail.html",
        {
            "request": request,
            "user": user,
            "course": course,
            "progress_by_lesson": progress["progress_by_lesson"],
            "course_progress": progress,
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
    completed_lessons = await db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user.id,
            LessonProgress.completed.is_(True),
        )
    )
    courses_list = (
        (
            await db.execute(
                select(Course)
                .where(Course.is_published.is_(True))
                .options(selectinload(Course.lessons))
            )
        )
        .scalars()
        .all()
    )
    completed_courses = 0
    for course in courses_list:
        progress = await get_course_progress(db, user, course)
        if progress["is_completed"]:
            completed_courses += 1

    focus_minutes_total = await db.scalar(
        select(func.coalesce(func.sum(FocusSession.duration_minutes), 0)).where(
            FocusSession.user_id == user.id,
            FocusSession.completed.is_(True),
        )
    )
    active_site_seconds = await db.scalar(
        select(func.coalesce(func.sum(UserActivityDay.seconds), 0)).where(
            UserActivityDay.user_id == user.id,
            UserActivityDay.activity_type == "site",
        )
    )
    pvp_total = await db.scalar(
        select(func.count(PvpBattle.id)).where(
            (PvpBattle.challenger_id == user.id) | (PvpBattle.opponent_id == user.id)
        )
    )
    pvp_wins = await db.scalar(
        select(func.count(PvpBattle.id)).where(PvpBattle.winner_id == user.id)
    )
    pvp_ties = await db.scalar(
        select(func.count(PvpBattle.id)).where(
            ((PvpBattle.challenger_id == user.id) | (PvpBattle.opponent_id == user.id)),
            PvpBattle.status == BattleStatus.FINISHED,
            PvpBattle.winner_id.is_(None),
        )
    )
    pvp_finished = await db.scalar(
        select(func.count(PvpBattle.id)).where(
            ((PvpBattle.challenger_id == user.id) | (PvpBattle.opponent_id == user.id)),
            PvpBattle.status == BattleStatus.FINISHED,
        )
    )
    pvp_losses = max(
        0, int(pvp_finished or 0) - int(pvp_wins or 0) - int(pvp_ties or 0)
    )
    lifetime_earned_points = await db.scalar(
        select(func.coalesce(func.sum(CurrencyTransaction.amount), 0)).where(
            CurrencyTransaction.user_id == user.id,
            CurrencyTransaction.amount > 0,
        )
    )
    lifetime_earned_points = int(lifetime_earned_points or 0)
    level = max(1, lifetime_earned_points // 100 + 1)
    next_level_points = level * 100
    level_progress = min(100, int(lifetime_earned_points % 100))
    onboarding = await db.scalar(
        select(UserOnboarding).where(UserOnboarding.user_id == user.id)
    )
    recent_battles = (
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

    profile_stats = {
        "completed_lessons": completed_lessons or 0,
        "completed_courses": completed_courses,
        "focus_minutes_total": int(focus_minutes_total or 0),
        "active_site_hours": round(int(active_site_seconds or 0) / 3600, 1),
        "pvp_total": pvp_total or 0,
        "pvp_wins": pvp_wins or 0,
        "pvp_losses": pvp_losses,
        "pvp_ties": pvp_ties or 0,
        "lifetime_earned_points": lifetime_earned_points,
        "level": level,
        "next_level_points": next_level_points,
        "level_progress": level_progress,
    }
    return templates(request).TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "achievements": achievements,
            "equipped_by_type": equipped_by_type,
            "study_hours_total": round((study_seconds or 0) / 3600, 1),
            "profile_stats": profile_stats,
            "onboarding": onboarding,
            "recent_battles": recent_battles,
        },
    )
