from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.validation import clamp_int
from app.models.course import Course, Lesson, LessonProgress
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.achievements import evaluate_learning_achievements
from app.services.course_progress import maybe_award_course_completion
from app.services.llm import recent_lesson_interactions, user_llm_requests_today
from app.services.rewards import add_skill_points
from app.services.streaks import sync_user_streak
from app.services.video import to_embed_url, video_tracking_provider

router = APIRouter(prefix="/learn", tags=["learning"])


def templates(request: Request):
    return request.app.state.templates


@router.get("/lessons/{lesson_id}")
async def lesson_page(
    lesson_id: int, request: Request, db: DbSession, user: User = Depends(require_user)
):
    lesson = (
        await db.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.course).selectinload(Course.lessons))
        )
    ).scalar_one()
    progress = (
        await db.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == user.id,
                LessonProgress.lesson_id == lesson.id,
            )
        )
    ).scalar_one_or_none()
    course_lessons = sorted(
        lesson.course.lessons, key=lambda item: (item.position, item.id)
    )
    lesson_index = next(
        (index for index, item in enumerate(course_lessons) if item.id == lesson.id), 0
    )
    previous_lesson = course_lessons[lesson_index - 1] if lesson_index > 0 else None
    next_lesson = (
        course_lessons[lesson_index + 1]
        if lesson_index + 1 < len(course_lessons)
        else None
    )
    outline_progress = (
        (
            await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == user.id,
                    LessonProgress.lesson_id.in_([item.id for item in course_lessons]),
                )
            )
        )
        .scalars()
        .all()
    )
    outline_progress_by_lesson = {item.lesson_id: item for item in outline_progress}
    watched_seconds = int(progress.watched_seconds or 0) if progress else 0
    duration_seconds = max(lesson.duration_minutes * 60, 1)
    watched_percent = min(100, int(watched_seconds * 100 / duration_seconds))
    settings = get_settings()
    ai_history = await recent_lesson_interactions(db, user, lesson.id)
    ai_used_today = await user_llm_requests_today(db, user)
    return templates(request).TemplateResponse(
        request,
        "lesson.html",
        {
            "request": request,
            "user": user,
            "lesson": lesson,
            "course": lesson.course,
            "progress": progress,
            "embed_url": to_embed_url(lesson.video_url),
            "tracking_provider": video_tracking_provider(lesson.video_url),
            "watched_seconds": watched_seconds,
            "duration_seconds": duration_seconds,
            "watched_percent": watched_percent,
            "course_lessons": course_lessons,
            "previous_lesson": previous_lesson,
            "next_lesson": next_lesson,
            "outline_progress_by_lesson": outline_progress_by_lesson,
            "llm_enabled": settings.llm_enabled,
            "llm_daily_limit": settings.llm_daily_limit_per_user,
            "llm_used_today": ai_used_today,
            "ai_history": ai_history,
        },
    )


@router.post("/lessons/{lesson_id}/progress")
async def save_progress(
    lesson_id: int,
    request: Request,
    db: DbSession,
    user: User = Depends(require_user),
    watched_seconds: int = Form(0),
    completed: bool = Form(False),
):
    lesson = (
        await db.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.course))
        )
    ).scalar_one_or_none()
    progress = (
        await db.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == user.id,
                LessonProgress.lesson_id == lesson_id,
            )
        )
    ).scalar_one_or_none()

    if progress is None:
        progress = LessonProgress(user_id=user.id, lesson_id=lesson_id)
        db.add(progress)

    safe_watched_seconds = clamp_int(
        watched_seconds or 0,
        min_value=0,
        max_value=60 * 60 * 24,
        field_name="watched seconds",
    )
    progress.watched_seconds = max(progress.watched_seconds or 0, safe_watched_seconds)

    course_completed = False
    if completed and not progress.completed:
        progress.completed = True
        await add_skill_points(
            db,
            user,
            lesson.reward_points if lesson else 10,
            "Lesson completed",
            "lesson",
            lesson_id,
        )
        await evaluate_learning_achievements(db, user)
        await sync_user_streak(db, user)
        if lesson and lesson.course:
            course_completed = await maybe_award_course_completion(
                db, user, lesson.course
            )

    await db.commit()

    if lesson and lesson.course:
        query = "course_completed=1" if course_completed else "lesson_completed=1"
        return RedirectResponse(
            f"/courses/{lesson.course.slug}?{query}", status_code=303
        )
    return RedirectResponse("/courses?lesson_completed=1", status_code=303)
