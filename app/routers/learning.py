from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.course import Lesson, LessonProgress
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.achievements import evaluate_learning_achievements
from app.services.course_progress import maybe_award_course_completion
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
            .options(selectinload(Lesson.course))
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
    watched_seconds = int(progress.watched_seconds or 0) if progress else 0
    duration_seconds = max(lesson.duration_minutes * 60, 1)
    watched_percent = min(100, int(watched_seconds * 100 / duration_seconds))
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

    safe_watched_seconds = int(watched_seconds or 0)
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
