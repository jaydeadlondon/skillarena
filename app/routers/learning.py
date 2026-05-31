from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.course import Course, Lesson, LessonProgress
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.achievements import evaluate_learning_achievements
from app.services.rewards import add_skill_points
from app.services.video import to_embed_url

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

    await db.commit()

    if lesson and lesson.course:
        return RedirectResponse(
            f"/courses/{lesson.course.slug}?lesson_completed=1", status_code=303
        )
    return RedirectResponse("/courses?lesson_completed=1", status_code=303)
