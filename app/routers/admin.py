import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.validation import (
    ValidationError,
    clamp_int,
    clean_optional_text,
    clean_text,
    validate_choice,
    validate_hex_color_or_css,
    validate_url,
)
from app.models.ai import AIInteraction
from app.models.course import Course, Lesson, VideoProvider
from app.models.gamification import (
    Achievement,
    CosmeticItem,
    Quest,
    QuestFrequency,
    UserOnboarding,
)
from app.models.pvp import PvpQuestion
from app.models.user import User, UserRole
from app.routers.deps import DbSession, require_admin
from app.services.llm import (
    LLMServiceError,
    build_quest_generation_prompt,
    build_quiz_generation_prompt,
    call_openai_compatible_chat,
    compact_json_from_text,
    ensure_llm_available,
    get_llm_config,
    quest_generator_system_prompt,
    quiz_generator_system_prompt,
    validate_generated_quest_items,
    validate_generated_quiz_items,
)
from app.services.rewards import add_skill_points

router = APIRouter(prefix="/admin", tags=["admin"])


def templates(request: Request):
    return request.app.state.templates


def validation_redirect(location: str, exc: ValidationError) -> RedirectResponse:
    return RedirectResponse(
        f"{location}?error=validation-{str(exc).replace(' ', '-').lower()}",
        status_code=303,
    )


@router.get("")
async def admin_dashboard(
    request: Request, db: DbSession, user: User = Depends(require_admin)
):
    courses = (
        (await db.execute(select(Course).order_by(Course.created_at.desc()).limit(8)))
        .scalars()
        .all()
    )
    quests = (
        (await db.execute(select(Quest).order_by(Quest.created_at.desc()).limit(8)))
        .scalars()
        .all()
    )
    achievements = (
        (
            await db.execute(
                select(Achievement).order_by(Achievement.created_at.desc()).limit(8)
            )
        )
        .scalars()
        .all()
    )
    questions = (
        (
            await db.execute(
                select(PvpQuestion).order_by(PvpQuestion.created_at.desc()).limit(8)
            )
        )
        .scalars()
        .all()
    )
    users = (
        (await db.execute(select(User).order_by(User.created_at.desc()).limit(8)))
        .scalars()
        .all()
    )
    cosmetics = (
        (
            await db.execute(
                select(CosmeticItem).order_by(CosmeticItem.created_at.desc()).limit(8)
            )
        )
        .scalars()
        .all()
    )

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
async def admin_users(
    request: Request, db: DbSession, user: User = Depends(require_admin)
):
    users = (
        (await db.execute(select(User).order_by(User.created_at.desc())))
        .scalars()
        .all()
    )
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
        return RedirectResponse(
            "/admin/users?error=cannot-demote-yourself", status_code=303
        )
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
    await add_skill_points(
        db, target, amount, reason or "Admin adjustment", "admin_user", target.id
    )
    await db.commit()
    return RedirectResponse("/admin/users?success=points-updated", status_code=303)


@router.get("/cosmetics")
async def admin_cosmetics(
    request: Request, db: DbSession, user: User = Depends(require_admin)
):
    cosmetics = (
        (
            await db.execute(
                select(CosmeticItem).order_by(
                    CosmeticItem.item_type, CosmeticItem.price_points, CosmeticItem.name
                )
            )
        )
        .scalars()
        .all()
    )
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
    try:
        item_type = validate_choice(
            item_type.strip(),
            allowed={"profile_frame", "profile_background", "aura"},
            field_name="item type",
        )
        code = (
            clean_text(code, max_length=80, field_name="code").lower().replace(" ", "_")
        )
        name = clean_text(name, max_length=120, field_name="name")
        price_points = clamp_int(
            price_points, min_value=0, max_value=100000, field_name="price"
        )
        preview_value = validate_hex_color_or_css(preview_value)
    except ValidationError as exc:
        return validation_redirect("/admin/cosmetics", exc)
    db.add(
        CosmeticItem(
            code=code,
            name=name,
            item_type=item_type,
            price_points=price_points,
            preview_value=preview_value,
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
        return RedirectResponse(
            "/admin/cosmetics?error=item-not-found", status_code=303
        )
    try:
        item_type = validate_choice(
            item_type.strip(),
            allowed={"profile_frame", "profile_background", "aura"},
            field_name="item type",
        )
        cosmetic.name = clean_text(name, max_length=120, field_name="name")
        cosmetic.item_type = item_type
        cosmetic.price_points = clamp_int(
            price_points, min_value=0, max_value=100000, field_name="price"
        )
        cosmetic.preview_value = validate_hex_color_or_css(preview_value)
    except ValidationError as exc:
        return validation_redirect("/admin/cosmetics", exc)
    await db.commit()
    return RedirectResponse("/admin/cosmetics?success=updated", status_code=303)


@router.post("/cosmetics/{item_id}/toggle")
async def toggle_cosmetic(
    item_id: int, db: DbSession, user: User = Depends(require_admin)
):
    cosmetic = await db.get(CosmeticItem, item_id)
    if cosmetic:
        cosmetic.is_active = not cosmetic.is_active
        await db.commit()
    return RedirectResponse("/admin/cosmetics?success=toggled", status_code=303)


@router.get("/courses")
async def admin_courses(
    request: Request, db: DbSession, user: User = Depends(require_admin)
):
    courses = (
        (
            await db.execute(
                select(Course)
                .options(selectinload(Course.lessons))
                .order_by(Course.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return templates(request).TemplateResponse(
        request,
        "admin_courses.html",
        {"request": request, "user": user, "courses": courses},
    )


@router.get("/courses/{course_id}")
async def admin_course_detail(
    course_id: int, request: Request, db: DbSession, user: User = Depends(require_admin)
):
    course = (
        await db.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.lessons))
        )
    ).scalar_one_or_none()
    if course is None:
        return RedirectResponse(
            "/admin/courses?error=course-not-found", status_code=303
        )
    return templates(request).TemplateResponse(
        request,
        "admin_course_detail.html",
        {"request": request, "user": user, "course": course},
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
    try:
        title = clean_text(title, max_length=180, field_name="title")
        slug = clean_text(slug, max_length=200, field_name="slug").lower()
        description = clean_text(description, max_length=5000, field_name="description")
        category = (
            clean_text(category, max_length=80, field_name="category", required=False)
            or "General"
        )
    except ValidationError as exc:
        return validation_redirect("/admin/courses", exc)
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
    return RedirectResponse("/admin/courses?success=created", status_code=303)


@router.post("/courses/{course_id}/update")
async def update_course(
    course_id: int,
    db: DbSession,
    user: User = Depends(require_admin),
    title: str = Form(...),
    slug: str = Form(...),
    description: str = Form(...),
    category: str = Form("General"),
    reward_points: int = Form(100),
    cover_image_url: str = Form(""),
):
    course = await db.get(Course, course_id)
    if course is None:
        return RedirectResponse(
            "/admin/courses?error=course-not-found", status_code=303
        )
    try:
        course.title = clean_text(title, max_length=180, field_name="title")
        course.slug = clean_text(slug, max_length=200, field_name="slug").lower()
        course.description = clean_text(
            description, max_length=5000, field_name="description"
        )
        course.category = (
            clean_text(category, max_length=80, field_name="category", required=False)
            or "General"
        )
        course.reward_points = clamp_int(
            reward_points, min_value=0, max_value=100000, field_name="reward points"
        )
        course.cover_image_url = (
            validate_url(cover_image_url, field_name="cover image URL", required=False)
            or None
        )
    except ValidationError as exc:
        return validation_redirect(f"/admin/courses/{course.id}", exc)
    await db.commit()
    return RedirectResponse(
        f"/admin/courses/{course.id}?success=updated", status_code=303
    )


@router.post("/courses/{course_id}/toggle")
async def toggle_course(
    course_id: int, db: DbSession, user: User = Depends(require_admin)
):
    course = await db.get(Course, course_id)
    if course:
        course.is_published = not course.is_published
        await db.commit()
        return RedirectResponse(
            f"/admin/courses/{course.id}?success=course-toggled", status_code=303
        )
    return RedirectResponse("/admin/courses?error=course-not-found", status_code=303)


@router.post("/courses/{course_id}/delete")
async def delete_course(
    course_id: int, db: DbSession, user: User = Depends(require_admin)
):
    course = await db.get(Course, course_id)
    if course is None:
        return RedirectResponse(
            "/admin/courses?error=course-not-found", status_code=303
        )
    await db.delete(course)
    await db.commit()
    return RedirectResponse("/admin/courses?success=deleted", status_code=303)


@router.post("/courses/{course_id}/lessons")
async def create_course_lesson(
    course_id: int,
    db: DbSession,
    user: User = Depends(require_admin),
    title: str = Form(...),
    position: int = Form(1),
    video_url: str = Form(...),
    duration_minutes: int = Form(10),
    reward_points: int = Form(10),
    content: str = Form(""),
):
    course = await db.get(Course, course_id)
    if course is None:
        return RedirectResponse(
            "/admin/courses?error=course-not-found", status_code=303
        )
    try:
        title = clean_text(title, max_length=180, field_name="lesson title")
        position = clamp_int(
            position, min_value=1, max_value=10000, field_name="position"
        )
        video_url = validate_url(video_url, field_name="video URL")
        duration_minutes = clamp_int(
            duration_minutes, min_value=1, max_value=600, field_name="duration"
        )
        reward_points = clamp_int(
            reward_points, min_value=0, max_value=10000, field_name="reward points"
        )
        content = (
            clean_text(content, max_length=20000, field_name="content", required=False)
            or "Stay focused: complete this small step and claim your reward."
        )
    except ValidationError as exc:
        return validation_redirect(f"/admin/courses/{course.id}", exc)
    db.add(
        Lesson(
            course_id=course.id,
            title=title,
            position=position,
            video_provider=VideoProvider.YOUTUBE,
            video_url=video_url,
            duration_minutes=duration_minutes,
            reward_points=reward_points,
            content=content,
        )
    )
    await db.commit()
    return RedirectResponse(
        f"/admin/courses/{course.id}?success=lesson-created", status_code=303
    )


@router.post("/lessons/{lesson_id}/update")
async def update_lesson(
    lesson_id: int,
    db: DbSession,
    user: User = Depends(require_admin),
    title: str = Form(...),
    position: int = Form(1),
    video_url: str = Form(...),
    duration_minutes: int = Form(10),
    reward_points: int = Form(10),
    content: str = Form(""),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        return RedirectResponse(
            "/admin/courses?error=lesson-not-found", status_code=303
        )
    try:
        lesson.title = clean_text(title, max_length=180, field_name="lesson title")
        lesson.position = clamp_int(
            position, min_value=1, max_value=10000, field_name="position"
        )
        lesson.video_url = validate_url(video_url, field_name="video URL")
        lesson.duration_minutes = clamp_int(
            duration_minutes, min_value=1, max_value=600, field_name="duration"
        )
        lesson.reward_points = clamp_int(
            reward_points, min_value=0, max_value=10000, field_name="reward points"
        )
        lesson.content = (
            clean_text(content, max_length=20000, field_name="content", required=False)
            or ""
        )
    except ValidationError as exc:
        return validation_redirect(f"/admin/courses/{lesson.course_id}", exc)
    await db.commit()
    return RedirectResponse(
        f"/admin/courses/{lesson.course_id}?success=lesson-updated", status_code=303
    )


@router.post("/lessons/{lesson_id}/delete")
async def delete_lesson(
    lesson_id: int, db: DbSession, user: User = Depends(require_admin)
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        return RedirectResponse(
            "/admin/courses?error=lesson-not-found", status_code=303
        )
    course_id = lesson.course_id
    await db.delete(lesson)
    await db.commit()
    return RedirectResponse(
        f"/admin/courses/{course_id}?success=lesson-deleted", status_code=303
    )


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
    try:
        title = clean_text(title, max_length=180, field_name="lesson title")
        position = clamp_int(
            position, min_value=1, max_value=10000, field_name="position"
        )
        video_url = validate_url(video_url, field_name="video URL")
        duration_minutes = clamp_int(
            duration_minutes, min_value=1, max_value=600, field_name="duration"
        )
    except ValidationError as exc:
        return validation_redirect(f"/admin/courses/{course_id}", exc)
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
    return RedirectResponse(
        f"/admin/courses/{course_id}?success=lesson-created", status_code=303
    )


@router.post("/ai-generate-quests")
async def ai_generate_quests_preview(
    request: Request,
    db: DbSession,
    user: User = Depends(require_admin),
    count: int = Form(3),
    frequency: str = Form("daily"),
    user_goal: str = Form(""),
    focus_challenge: str = Form(""),
    preferred_minutes: int = Form(25),
):
    onboarding = await db.scalar(
        select(UserOnboarding).where(UserOnboarding.user_id == user.id)
    )
    if not user_goal and onboarding:
        user_goal = onboarding.learning_goal
    if not focus_challenge and onboarding:
        focus_challenge = onboarding.focus_challenge
    if onboarding and preferred_minutes == 25:
        preferred_minutes = onboarding.preferred_session_minutes
    try:
        await ensure_llm_available(db, user)
        provider, _, model = get_llm_config()
        prompt = build_quest_generation_prompt(
            count,
            frequency,
            user_goal or "Build a consistent learning habit",
            focus_challenge or "consistency",
            preferred_minutes,
        )
        raw_response = await call_openai_compatible_chat(
            quest_generator_system_prompt(), prompt
        )
        items = validate_generated_quest_items(
            compact_json_from_text(raw_response), max(1, min(int(count), 10)), frequency
        )
        db.add(
            AIInteraction(
                user_id=user.id,
                context_type="admin_quest_preview",
                context_id=None,
                prompt_type="quest_generator_preview",
                prompt=prompt,
                response=raw_response,
                provider=provider,
                model=model,
            )
        )
        await db.commit()
        return templates(request).TemplateResponse(
            request,
            "admin_ai_quest_preview.html",
            {"request": request, "user": user, "items": items},
        )
    except Exception:
        await db.rollback()
        return RedirectResponse(
            "/admin?error=ai-quest-generation-failed", status_code=303
        )


@router.post("/ai-save-quests")
async def ai_save_quests(
    db: DbSession,
    user: User = Depends(require_admin),
    generated_json: str = Form(...),
    selected: list[int] = Form(default=[]),
):
    try:
        items = json.loads(generated_json)
        selected_set = {int(index) for index in selected}
        created = 0
        for index, item in enumerate(items):
            if index not in selected_set:
                continue
            quest_frequency = (
                QuestFrequency.WEEKLY
                if item["frequency"] == "weekly"
                else QuestFrequency.DAILY
            )
            db.add(
                Quest(
                    title=item["title"],
                    description=item["description"],
                    frequency=quest_frequency,
                    target_metric=item["target_metric"],
                    target_value=int(item["target_value"]),
                    reward_points=int(item["reward_points"]),
                    is_active=True,
                )
            )
            created += 1
        await db.commit()
        return RedirectResponse(
            f"/admin?success=ai-quests-generated&created={created}", status_code=303
        )
    except Exception:
        await db.rollback()
        return RedirectResponse("/admin?error=ai-quest-save-failed", status_code=303)


@router.post("/quests")
async def create_quest(
    db: DbSession,
    user: User = Depends(require_admin),
    title: str = Form(...),
    description: str = Form(...),
    frequency: str = Form("daily"),
    target_metric: str = Form("study_minutes"),
    target_value: int = Form(20),
    reward_points: int = Form(25),
):
    try:
        title = clean_text(title, max_length=160, field_name="quest title")
        description = clean_text(
            description, max_length=2000, field_name="quest description"
        )
        frequency = validate_choice(
            frequency, allowed={"daily", "weekly"}, field_name="frequency"
        )
        target_metric = validate_choice(
            target_metric,
            allowed={
                "study_minutes",
                "focus_minutes",
                "lessons_completed",
                "pvp_wins",
                "pvp_participation",
            },
            field_name="target metric",
        )
        target_value = clamp_int(
            target_value, min_value=1, max_value=10000, field_name="target value"
        )
        reward_points = clamp_int(
            reward_points, min_value=0, max_value=100000, field_name="reward points"
        )
    except ValidationError as exc:
        return validation_redirect("/admin", exc)
    quest_frequency = (
        QuestFrequency.WEEKLY
        if frequency == QuestFrequency.WEEKLY.value
        else QuestFrequency.DAILY
    )
    db.add(
        Quest(
            title=title,
            description=description,
            frequency=quest_frequency,
            target_metric=target_metric,
            target_value=target_value,
            reward_points=reward_points,
        )
    )
    await db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/quests/{quest_id}/toggle")
async def toggle_quest(
    quest_id: int, db: DbSession, user: User = Depends(require_admin)
):
    quest = await db.get(Quest, quest_id)
    if quest:
        quest.is_active = not quest.is_active
        await db.commit()
    return RedirectResponse("/admin?success=quest-toggled", status_code=303)


@router.post("/courses/{course_id}/ai-generate-quiz")
async def ai_generate_course_quiz_preview(
    course_id: int,
    request: Request,
    db: DbSession,
    user: User = Depends(require_admin),
    lesson_id: int = Form(...),
    count: int = Form(5),
    difficulty: int = Form(1),
):
    lesson = (
        await db.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id, Lesson.course_id == course_id)
            .options(selectinload(Lesson.course))
        )
    ).scalar_one_or_none()
    if lesson is None:
        return RedirectResponse(
            f"/admin/courses/{course_id}?error=lesson-not-found", status_code=303
        )
    if not lesson.content or len(lesson.content.strip()) < 40:
        return RedirectResponse(
            f"/admin/courses/{course_id}?error=lesson-content-too-short",
            status_code=303,
        )
    try:
        await ensure_llm_available(db, user)
        provider, _, model = get_llm_config()
        prompt = build_quiz_generation_prompt(lesson, count, difficulty)
        raw_response = await call_openai_compatible_chat(
            quiz_generator_system_prompt(), prompt
        )
        items = validate_generated_quiz_items(
            compact_json_from_text(raw_response), max(1, min(int(count), 10))
        )
        db.add(
            AIInteraction(
                user_id=user.id,
                context_type="admin_quiz_preview",
                context_id=lesson.id,
                prompt_type="quiz_generator_preview",
                prompt=prompt,
                response=raw_response,
                provider=provider,
                model=model,
            )
        )
        await db.commit()
        return templates(request).TemplateResponse(
            request,
            "admin_ai_quiz_preview.html",
            {
                "request": request,
                "user": user,
                "course_id": course_id,
                "lesson": lesson,
                "items": items,
                "difficulty": difficulty,
            },
        )
    except Exception:
        await db.rollback()
        return RedirectResponse(
            f"/admin/courses/{course_id}?error=ai-generation-failed", status_code=303
        )


@router.post("/courses/{course_id}/ai-save-quiz")
async def ai_save_course_quiz(
    course_id: int,
    db: DbSession,
    user: User = Depends(require_admin),
    generated_json: str = Form(...),
    difficulty: int = Form(1),
    selected: list[int] = Form(default=[]),
):
    try:
        items = json.loads(generated_json)
        selected_set = {int(index) for index in selected}
        created = 0
        for index, item in enumerate(items):
            if index not in selected_set:
                continue
            db.add(
                PvpQuestion(
                    course_id=course_id,
                    difficulty=max(1, min(int(difficulty), 3)),
                    is_active=True,
                    question=item["question"],
                    option_a=item["option_a"],
                    option_b=item["option_b"],
                    option_c=item["option_c"],
                    option_d=item["option_d"],
                    correct_option=item["correct_option"],
                )
            )
            created += 1
        await db.commit()
        return RedirectResponse(
            f"/admin/courses/{course_id}?success=ai-quiz-generated&created={created}",
            status_code=303,
        )
    except Exception:
        await db.rollback()
        return RedirectResponse(
            f"/admin/courses/{course_id}?error=ai-quiz-save-failed", status_code=303
        )


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
    try:
        question = clean_text(question, max_length=1000, field_name="question")
        option_a = clean_text(option_a, max_length=255, field_name="option A")
        option_b = clean_text(option_b, max_length=255, field_name="option B")
        option_c = clean_text(option_c, max_length=255, field_name="option C")
        option_d = clean_text(option_d, max_length=255, field_name="option D")
        correct_option = validate_choice(
            correct_option.upper()[:1],
            allowed={"A", "B", "C", "D"},
            field_name="correct option",
        )
    except ValidationError as exc:
        return validation_redirect("/admin", exc)
    db.add(
        PvpQuestion(
            question=question,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
        )
    )
    await db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/pvp-questions/{question_id}/toggle")
async def toggle_pvp_question(
    question_id: int, db: DbSession, user: User = Depends(require_admin)
):
    question = await db.get(PvpQuestion, question_id)
    if question:
        question.is_active = not question.is_active
        await db.commit()
    return RedirectResponse("/admin?success=question-toggled", status_code=303)
