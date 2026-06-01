from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, Lesson, LessonProgress
from app.models.user import CurrencyTransaction, User
from app.services.rewards import add_skill_points


async def get_course_progress(
    db: AsyncSession, user: User, course: Course
) -> dict[str, Any]:
    lesson_ids = [lesson.id for lesson in course.lessons]
    total = len(lesson_ids)
    if total == 0:
        return {
            "total": 0,
            "completed": 0,
            "percent": 0,
            "next_lesson": None,
            "is_completed": False,
            "course_reward_claimed": False,
        }

    progresses = (
        (
            await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == user.id,
                    LessonProgress.lesson_id.in_(lesson_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    progress_by_lesson = {progress.lesson_id: progress for progress in progresses}
    completed = sum(
        1
        for lesson_id in lesson_ids
        if progress_by_lesson.get(lesson_id) and progress_by_lesson[lesson_id].completed
    )
    next_lesson = None
    for lesson in course.lessons:
        progress = progress_by_lesson.get(lesson.id)
        if not progress or not progress.completed:
            next_lesson = lesson
            break

    is_completed = completed == total
    reward_claimed = await db.scalar(
        select(func.count(CurrencyTransaction.id)).where(
            CurrencyTransaction.user_id == user.id,
            CurrencyTransaction.reference_type == "course",
            CurrencyTransaction.reference_id == course.id,
            CurrencyTransaction.reason == "Course completed",
        )
    )

    return {
        "total": total,
        "completed": completed,
        "percent": int(completed * 100 / total) if total else 0,
        "next_lesson": next_lesson,
        "is_completed": is_completed,
        "course_reward_claimed": bool(reward_claimed),
        "progress_by_lesson": progress_by_lesson,
    }


async def maybe_award_course_completion(
    db: AsyncSession, user: User, course: Course
) -> bool:
    progress = await get_course_progress(db, user, course)
    if not progress["is_completed"] or progress["course_reward_claimed"]:
        return False
    await add_skill_points(
        db, user, course.reward_points, "Course completed", "course", course.id
    )
    return True


async def find_continue_lesson(
    db: AsyncSession, user: User
) -> tuple[Course | None, Lesson | None, dict[str, Any] | None]:
    courses = (
        (
            await db.execute(
                select(Course)
                .where(Course.is_published.is_(True))
                .options(selectinload(Course.lessons))
                .order_by(Course.title)
            )
        )
        .scalars()
        .all()
    )

    best_candidate: tuple[Course | None, Lesson | None, dict[str, Any] | None] = (
        None,
        None,
        None,
    )
    best_completed = -1
    for course in courses:
        progress = await get_course_progress(db, user, course)
        if progress["is_completed"]:
            continue
        next_lesson = progress["next_lesson"]
        if next_lesson and progress["completed"] > best_completed:
            best_candidate = (course, next_lesson, progress)
            best_completed = progress["completed"]

    if best_candidate[1] is not None:
        return best_candidate

    for course in courses:
        if course.lessons:
            progress = await get_course_progress(db, user, course)
            return course, course.lessons[0], progress
    return None, None, None
