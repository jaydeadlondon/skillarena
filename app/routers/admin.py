from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.models.course import Course, Lesson, VideoProvider
from app.models.gamification import Achievement, Quest, QuestFrequency
from app.models.pvp import PvpQuestion
from app.models.user import User
from app.routers.deps import DbSession, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def admin_dashboard(
    request: Request, db: DbSession, user: User = Depends(require_admin)
):
    courses = (
        (await db.execute(select(Course).order_by(Course.created_at.desc())))
        .scalars()
        .all()
    )
    quests = (
        (await db.execute(select(Quest).order_by(Quest.created_at.desc())))
        .scalars()
        .all()
    )
    achievements = (
        (await db.execute(select(Achievement).order_by(Achievement.created_at.desc())))
        .scalars()
        .all()
    )
    questions = (
        (
            await db.execute(
                select(PvpQuestion).order_by(PvpQuestion.created_at.desc()).limit(10)
            )
        )
        .scalars()
        .all()
    )
    users = (
        (await db.execute(select(User).order_by(User.created_at.desc()).limit(20)))
        .scalars()
        .all()
    )
    return templates(request).TemplateResponse(
        request,
        "admin.html",
        {
            "request": request,
            "user": user,
            "courses": courses,
            "quests": quests,
            "achievements": achievements,
            "questions": questions,
            "users": users,
        },
    )


@router.post("/courses")
async def create_course(
    db: DbSession,
    user: User = Depends(require_admin),
    title: str = Form(...),
    slug: str = Form(...),
    description: str = Form(...),
    category: str = Form("General"),
):
    db.add(
        Course(
            title=title,
            slug=slug,
            description=description,
            category=category,
            is_published=True,
        )
    )
    await db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/lessons")
async def create_lesson(
    db: DbSession,
    user: User = Depends(require_admin),
    course_id: int = Form(...),
    title: str = Form(...),
    position: int = Form(1),
    video_url: str = Form(...),
    duration_minutes: int = Form(10),
):
    db.add(
        Lesson(
            course_id=course_id,
            title=title,
            position=position,
            video_provider=VideoProvider.YOUTUBE,
            video_url=video_url,
            duration_minutes=duration_minutes,
            content="Stay focused: complete this small step and claim your reward.",
        )
    )
    await db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/quests")
async def create_quest(
    db: DbSession,
    user: User = Depends(require_admin),
    title: str = Form(...),
    description: str = Form(...),
    target_metric: str = Form("study_minutes"),
    target_value: int = Form(20),
    reward_points: int = Form(25),
):
    db.add(
        Quest(
            title=title,
            description=description,
            frequency=QuestFrequency.DAILY,
            target_metric=target_metric,
            target_value=target_value,
            reward_points=reward_points,
        )
    )
    await db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/pvp-questions")
async def create_pvp_question(
    db: DbSession,
    user: User = Depends(require_admin),
    question: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct_option: str = Form(...),
):
    db.add(
        PvpQuestion(
            question=question,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option.upper()[:1],
        )
    )
    await db.commit()
    return RedirectResponse("/admin", status_code=303)
