from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.models.course import Course, Lesson, VideoProvider
from app.models.gamification import Achievement, CosmeticItem, Quest, QuestFrequency
from app.models.pvp import PvpQuestion
from app.models.user import User, UserRole
from app.routers.deps import DbSession, require_admin
from app.services.rewards import add_skill_points

router = APIRouter(prefix="/admin", tags=["admin"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def admin_dashboard(request: Request, db: DbSession, user: User = Depends(require_admin)):
    courses = (await db.execute(select(Course).order_by(Course.created_at.desc()).limit(8))).scalars().all()
    quests = (await db.execute(select(Quest).order_by(Quest.created_at.desc()).limit(8))).scalars().all()
    achievements = (await db.execute(select(Achievement).order_by(Achievement.created_at.desc()).limit(8))).scalars().all()
    questions = (await db.execute(select(PvpQuestion).order_by(PvpQuestion.created_at.desc()).limit(8))).scalars().all()
    users = (await db.execute(select(User).order_by(User.created_at.desc()).limit(8))).scalars().all()
    cosmetics = (await db.execute(select(CosmeticItem).order_by(CosmeticItem.created_at.desc()).limit(8))).scalars().all()

    stats = {
        "users": await db.scalar(select(func.count(User.id))) or 0,
        "courses": await db.scalar(select(func.count(Course.id))) or 0,
        "quests": await db.scalar(select(func.count(Quest.id))) or 0,
        "questions": await db.scalar(select(func.count(PvpQuestion.id))) or 0,
        "cosmetics": await db.scalar(select(func.count(CosmeticItem.id))) or 0,
    }
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
            "cosmetics": cosmetics,
            "stats": stats,
        },
    )


@router.get("/users")
async def admin_users(request: Request, db: DbSession, user: User = Depends(require_admin)):
    users = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return templates(request).TemplateResponse(
        request,
        "admin_users.html",
        {"request": request, "user": user, "users": users},
    )


@router.post("/users/{target_user_id}/role")
async def update_user_role(
    target_user_id: int,
    db: DbSession,
    user: User = Depends(require_admin),
    role: str = Form(...),
):
    target = await db.get(User, target_user_id)
    if target is None:
        return RedirectResponse("/admin/users?error=user-not-found", status_code=303)
    if target.id == user.id and role != UserRole.ADMIN.value:
        return RedirectResponse("/admin/users?error=cannot-demote-yourself", status_code=303)
    target.role = UserRole.ADMIN if role == UserRole.ADMIN.value else UserRole.USER
    await db.commit()
    return RedirectResponse("/admin/users?success=role-updated", status_code=303)


@router.post("/users/{target_user_id}/points")
async def adjust_user_points(
    target_user_id: int,
    db: DbSession,
    user: User = Depends(require_admin),
    amount: int = Form(...),
    reason: str = Form("Admin adjustment"),
):
    target = await db.get(User, target_user_id)
    if target is None:
        return RedirectResponse("/admin/users?error=user-not-found", status_code=303)
    if target.skill_points + amount < 0:
        return RedirectResponse("/admin/users?error=negative-balance", status_code=303)
    await add_skill_points(db, target, amount, reason or "Admin adjustment", "admin_user", target.id)
    await db.commit()
    return RedirectResponse("/admin/users?success=points-updated", status_code=303)


@router.get("/cosmetics")
async def admin_cosmetics(request: Request, db: DbSession, user: User = Depends(require_admin)):
    cosmetics = (
        await db.execute(select(CosmeticItem).order_by(CosmeticItem.item_type, CosmeticItem.price_points, CosmeticItem.name))
    ).scalars().all()
    return templates(request).TemplateResponse(
        request,
        "admin_cosmetics.html",
        {"request": request, "user": user, "cosmetics": cosmetics},
    )


@router.post("/cosmetics")
async def create_cosmetic(
    db: DbSession,
    user: User = Depends(require_admin),
    code: str = Form(...),
    name: str = Form(...),
    item_type: str = Form(...),
    price_points: int = Form(...),
    preview_value: str = Form(...),
):
    item_type = item_type.strip()
    if item_type not in {"profile_frame", "profile_background", "aura"}:
        return RedirectResponse("/admin/cosmetics?error=invalid-type", status_code=303)
    db.add(
        CosmeticItem(
            code=code.strip().lower().replace(" ", "_"),
            name=name.strip(),
            item_type=item_type,
            price_points=max(0, price_points),
            preview_value=preview_value.strip(),
            is_active=True,
        )
    )
    await db.commit()
    return RedirectResponse("/admin/cosmetics?success=created", status_code=303)


@router.post("/cosmetics/{item_id}/update")
async def update_cosmetic(
    item_id: int,
    db: DbSession,
    user: User = Depends(require_admin),
    name: str = Form(...),
    item_type: str = Form(...),
    price_points: int = Form(...),
    preview_value: str = Form(...),
):
    cosmetic = await db.get(CosmeticItem, item_id)
    if cosmetic is None:
        return RedirectResponse("/admin/cosmetics?error=item-not-found", status_code=303)
    if item_type not in {"profile_frame", "profile_background", "aura"}:
        return RedirectResponse("/admin/cosmetics?error=invalid-type", status_code=303)
    cosmetic.name = name.strip()
    cosmetic.item_type = item_type
    cosmetic.price_points = max(0, price_points)
    cosmetic.preview_value = preview_value.strip()
    await db.commit()
    return RedirectResponse("/admin/cosmetics?success=updated", status_code=303)


@router.post("/cosmetics/{item_id}/toggle")
async def toggle_cosmetic(item_id: int, db: DbSession, user: User = Depends(require_admin)):
    cosmetic = await db.get(CosmeticItem, item_id)
    if cosmetic:
        cosmetic.is_active = not cosmetic.is_active
        await db.commit()
    return RedirectResponse("/admin/cosmetics?success=toggled", status_code=303)


@router.post("/courses")
async def create_course(
    db: DbSession,
    user: User = Depends(require_admin),
    title: str = Form(...),
    slug: str = Form(...),
    description: str = Form(...),
    category: str = Form("General"),
):
    db.add(Course(title=title, slug=slug, description=description, category=category, is_published=True))
    await db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/courses/{course_id}/toggle")
async def toggle_course(course_id: int, db: DbSession, user: User = Depends(require_admin)):
    course = await db.get(Course, course_id)
    if course:
        course.is_published = not course.is_published
        await db.commit()
    return RedirectResponse("/admin?success=course-toggled", status_code=303)


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


@router.post("/quests/{quest_id}/toggle")
async def toggle_quest(quest_id: int, db: DbSession, user: User = Depends(require_admin)):
    quest = await db.get(Quest, quest_id)
    if quest:
        quest.is_active = not quest.is_active
        await db.commit()
    return RedirectResponse("/admin?success=quest-toggled", status_code=303)


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


@router.post("/pvp-questions/{question_id}/toggle")
async def toggle_pvp_question(question_id: int, db: DbSession, user: User = Depends(require_admin)):
    question = await db.get(PvpQuestion, question_id)
    if question:
        question.is_active = not question.is_active
        await db.commit()
    return RedirectResponse("/admin?success=question-toggled", status_code=303)
