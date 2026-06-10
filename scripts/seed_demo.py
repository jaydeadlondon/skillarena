import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models.ai  # noqa: F401,E402
import app.models.analytics  # noqa: F401,E402
import app.models.audit  # noqa: F401,E402
import app.models.course  # noqa: F401,E402
import app.models.gamification  # noqa: F401,E402
import app.models.pvp  # noqa: F401,E402
import app.models.telegram_payment  # noqa: F401,E402
import app.models.user  # noqa: F401,E402
from sqlalchemy import inspect, select  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.models.course import Course, Lesson, VideoProvider  # noqa: E402
from app.models.gamification import (  # noqa: E402
    Achievement,
    AchievementType,
    CosmeticItem,
    Quest,
    QuestFrequency,
)
from app.models.pvp import PvpQuestion  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


async def ensure_tables_exist() -> None:
    async with engine.begin() as conn:
        existing_tables = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
        required_tables = set(Base.metadata.tables.keys())
        missing_tables = sorted(required_tables - existing_tables)
        if missing_tables:
            print(f"Missing tables detected: {', '.join(missing_tables)}")
            await conn.run_sync(Base.metadata.create_all)
            print("Missing tables created.")


async def upsert_quest(
    db,
    *,
    title: str,
    description: str,
    frequency: QuestFrequency,
    target_metric: str,
    target_value: int,
    reward_points: int,
) -> None:
    quest = await db.scalar(select(Quest).where(Quest.title == title))
    if quest is None:
        db.add(
            Quest(
                title=title,
                description=description,
                frequency=frequency,
                target_metric=target_metric,
                target_value=target_value,
                reward_points=reward_points,
            )
        )
    else:
        quest.description = description
        quest.frequency = frequency
        quest.target_metric = target_metric
        quest.target_value = target_value
        quest.reward_points = reward_points
        quest.is_active = True


async def upsert_course_with_lessons(
    db, *, course_data: dict, lessons: list[dict]
) -> None:
    course = await db.scalar(select(Course).where(Course.slug == course_data["slug"]))
    if course is None:
        course = Course(**course_data)
        db.add(course)
        await db.flush()
    else:
        for key, value in course_data.items():
            setattr(course, key, value)
        await db.flush()

    for lesson_data in lessons:
        existing_lesson = await db.scalar(
            select(Lesson).where(
                Lesson.course_id == course.id,
                Lesson.position == lesson_data["position"],
            )
        )
        payload = dict(lesson_data)
        payload["course_id"] = course.id
        if existing_lesson is None:
            db.add(Lesson(**payload))
        else:
            for key, value in payload.items():
                setattr(existing_lesson, key, value)


async def upsert_achievement(
    db,
    *,
    code: str,
    title: str,
    description: str,
    achievement_type: AchievementType,
    threshold: int,
    reward_points: int,
    badge_icon: str,
) -> None:
    achievement = await db.scalar(select(Achievement).where(Achievement.code == code))
    if achievement is None:
        db.add(
            Achievement(
                code=code,
                title=title,
                description=description,
                achievement_type=achievement_type,
                threshold=threshold,
                reward_points=reward_points,
                badge_icon=badge_icon,
            )
        )
    else:
        achievement.title = title
        achievement.description = description
        achievement.achievement_type = achievement_type
        achievement.threshold = threshold
        achievement.reward_points = reward_points
        achievement.badge_icon = badge_icon


async def main() -> None:
    await ensure_tables_exist()

    async with AsyncSessionLocal() as db:
        courses = [
            (
                dict(
                    title="Focus Fundamentals",
                    slug="focus-fundamentals",
                    description="Build a simple focus ritual with tiny ADHD-friendly learning steps.",
                    category="Productivity",
                    difficulty="beginner",
                    estimated_minutes=35,
                    is_featured=True,
                    is_published=True,
                    reward_points=100,
                ),
                [
                    dict(
                        title="The 5-minute focus ritual",
                        position=1,
                        content="# Goal\nRemove one distraction and complete five focused minutes.\n\n## Key ideas\n- Start smaller than your motivation wants.\n- Remove one visible distraction before starting.\n- A tiny win is better than waiting for perfect focus.\n\n## Mini task\nPut your phone away, open one lesson, and focus for five minutes.\n\n> If you continue after five minutes, that is a bonus, not a requirement.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=inpok4MKVLM",
                        duration_minutes=5,
                        reward_points=10,
                    ),
                    dict(
                        title="Break big goals into tiny quests",
                        position=2,
                        content="# Goal\nTurn a large learning goal into small quests.\n\n## Key ideas\n- Big goals create friction.\n- Tiny quests tell your brain exactly what to do next.\n- A good quest can be finished in 5–20 minutes.\n\n## Mini task\nRewrite one big goal as three tiny actions.\n\nExample:\n```\nLearn JavaScript -> Watch one short lesson -> write one variable -> run one example\n```",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=arj7oStGLkU",
                        duration_minutes=10,
                        reward_points=15,
                    ),
                ],
            ),
            (
                dict(
                    title="JavaScript Basics",
                    slug="javascript-basics",
                    description="Learn the basic building blocks of JavaScript for interactive web pages.",
                    category="Programming",
                    difficulty="beginner",
                    estimated_minutes=90,
                    is_featured=True,
                    is_published=True,
                    reward_points=150,
                ),
                [
                    dict(
                        title="What is JavaScript?",
                        position=1,
                        content="# Goal\nUnderstand what JavaScript does on the web.\n\n## Key ideas\n- HTML describes structure.\n- CSS describes appearance.\n- JavaScript describes behavior.\n\n## Mini task\nFind one button on any website and describe what JavaScript might do when it is clicked.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=W6NZfCO5SIk",
                        duration_minutes=12,
                        reward_points=15,
                    ),
                    dict(
                        title="Variables and values",
                        position=2,
                        content="# Goal\nStore information in variables.\n\n## Key ideas\n- `let` creates a value that can change.\n- `const` creates a value that should not be reassigned.\n- Values can be strings, numbers, booleans, arrays, and objects.\n\n## Mini task\nWrite three variables: your name, your current level, and whether you studied today.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=edlFjlzxkSI",
                        duration_minutes=15,
                        reward_points=20,
                    ),
                    dict(
                        title="Functions",
                        position=3,
                        content="# Goal\nUnderstand functions as reusable actions.\n\n## Key ideas\n- A function groups code under a name.\n- Parameters let a function accept input.\n- `return` sends a value back.\n\n## Mini task\nWrite a function called `addPoints` that adds two numbers.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=N8ap4k_1QEQ",
                        duration_minutes=18,
                        reward_points=25,
                    ),
                ],
            ),
            (
                dict(
                    title="Python Basics",
                    slug="python-basics",
                    description="Start writing simple Python programs with variables, conditions, loops, and functions.",
                    category="Programming",
                    difficulty="beginner",
                    estimated_minutes=100,
                    is_featured=True,
                    is_published=True,
                    reward_points=150,
                ),
                [
                    dict(
                        title="What is Python?",
                        position=1,
                        content="# Goal\nUnderstand why Python is useful.\n\n## Key ideas\n- Python is readable and beginner-friendly.\n- It is used for web development, automation, data, AI, and scripts.\n- Python programs are made of small instructions.\n\n## Mini task\nWrite one thing you would like to automate with Python.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=kqtD5dpn9C8",
                        duration_minutes=12,
                        reward_points=15,
                    ),
                    dict(
                        title="Variables and data types",
                        position=2,
                        content="# Goal\nStore and use values in Python.\n\n## Key ideas\n- Variables point to values.\n- Common types include `str`, `int`, `float`, and `bool`.\n- `print()` shows output.\n\n## Mini task\nCreate variables for your name, age, and current study streak.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=Z1Yd7upQsXY",
                        duration_minutes=15,
                        reward_points=20,
                    ),
                    dict(
                        title="Conditions and loops",
                        position=3,
                        content="# Goal\nMake decisions and repeat actions.\n\n## Key ideas\n- `if` runs code only when a condition is true.\n- `for` repeats over a sequence.\n- `while` repeats while a condition stays true.\n\n## Mini task\nWrite an `if` statement that prints a reward message when points are above 100.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=6iF8Xb7Z3wQ",
                        duration_minutes=20,
                        reward_points=25,
                    ),
                ],
            ),
        ]
        for course_data, lesson_data in courses:
            await upsert_course_with_lessons(
                db, course_data=course_data, lessons=lesson_data
            )

        quests = [
            dict(
                title="Study for 20 minutes",
                description="Open lessons and collect at least 20 minutes of study time today.",
                frequency=QuestFrequency.DAILY,
                target_metric="study_minutes",
                target_value=20,
                reward_points=25,
            ),
            dict(
                title="Complete one lesson",
                description="Finish one lesson today and keep your momentum alive.",
                frequency=QuestFrequency.DAILY,
                target_metric="lessons_completed",
                target_value=1,
                reward_points=20,
            ),
            dict(
                title="Focus for 15 minutes",
                description="Complete focused learning time today.",
                frequency=QuestFrequency.DAILY,
                target_metric="focus_minutes",
                target_value=15,
                reward_points=25,
            ),
            dict(
                title="Win one quiz duel",
                description="Challenge another learner and win a PvP quiz battle.",
                frequency=QuestFrequency.DAILY,
                target_metric="pvp_wins",
                target_value=1,
                reward_points=40,
            ),
            dict(
                title="Study for 120 minutes this week",
                description="Build a strong weekly learning rhythm with two hours of study time.",
                frequency=QuestFrequency.WEEKLY,
                target_metric="study_minutes",
                target_value=120,
                reward_points=120,
            ),
            dict(
                title="Complete 3 lessons this week",
                description="Finish three lessons before the weekly reset.",
                frequency=QuestFrequency.WEEKLY,
                target_metric="lessons_completed",
                target_value=3,
                reward_points=90,
            ),
            dict(
                title="Focus for 60 minutes this week",
                description="Complete one hour of focus sessions this week.",
                frequency=QuestFrequency.WEEKLY,
                target_metric="focus_minutes",
                target_value=60,
                reward_points=80,
            ),
        ]
        for quest_data in quests:
            await upsert_quest(db, **quest_data)

        achievements = [
            dict(
                code="first_lesson",
                title="First Spark",
                description="Complete your first lesson.",
                achievement_type=AchievementType.LESSONS,
                threshold=1,
                reward_points=10,
                badge_icon="✨",
            ),
            dict(
                code="five_lessons",
                title="Quest Apprentice",
                description="Complete five lessons.",
                achievement_type=AchievementType.LESSONS,
                threshold=5,
                reward_points=25,
                badge_icon="📜",
            ),
            dict(
                code="ten_study_minutes",
                title="Focus Ember",
                description="Collect ten minutes of study time.",
                achievement_type=AchievementType.STUDY_MINUTES,
                threshold=10,
                reward_points=15,
                badge_icon="🕯️",
            ),
            dict(
                code="one_study_hour",
                title="Arcane Hour",
                description="Collect one full hour of study time.",
                achievement_type=AchievementType.STUDY_MINUTES,
                threshold=60,
                reward_points=40,
                badge_icon="⏳",
            ),
            dict(
                code="three_day_streak",
                title="Kindled Focus",
                description="Keep a 3-day learning streak.",
                achievement_type=AchievementType.STREAK,
                threshold=3,
                reward_points=30,
                badge_icon="🔥",
            ),
            dict(
                code="seven_day_streak",
                title="Flame Keeper",
                description="Keep a 7-day learning streak.",
                achievement_type=AchievementType.STREAK,
                threshold=7,
                reward_points=70,
                badge_icon="🔥",
            ),
            dict(
                code="first_duel",
                title="Arena Initiate",
                description="Participate in your first PvP quiz battle.",
                achievement_type=AchievementType.PVP_WINS,
                threshold=1,
                reward_points=10,
                badge_icon="⚔️",
            ),
            dict(
                code="first_pvp_win",
                title="Arena Victor",
                description="Win your first PvP quiz battle.",
                achievement_type=AchievementType.PVP_WINS,
                threshold=1,
                reward_points=30,
                badge_icon="🏆",
            ),
            dict(
                code="five_pvp_wins",
                title="Duel Champion",
                description="Win five PvP quiz battles.",
                achievement_type=AchievementType.PVP_WINS,
                threshold=5,
                reward_points=100,
                badge_icon="👑",
            ),
            dict(
                code="study_over_steam",
                title="Balance Breaker",
                description="Study more than you play on Steam over two weeks.",
                achievement_type=AchievementType.BALANCE,
                threshold=1,
                reward_points=100,
                badge_icon="⚖️",
            ),
        ]
        for achievement_data in achievements:
            await upsert_achievement(db, **achievement_data)

        cosmetics = [
            dict(
                code="violet_aura",
                name="Violet Aura",
                item_type="aura",
                price_points=120,
                preview_value="#8b5cf6",
            ),
            dict(
                code="gold_frame",
                name="Golden Frame",
                item_type="profile_frame",
                price_points=200,
                preview_value="#f7c948",
            ),
            dict(
                code="emerald_frame",
                name="Emerald Frame",
                item_type="profile_frame",
                price_points=90,
                preview_value="#36d399",
            ),
            dict(
                code="abyss_background",
                name="Abyss Background",
                item_type="profile_background",
                price_points=140,
                preview_value="#111827",
            ),
            dict(
                code="arcane_background",
                name="Arcane Background",
                item_type="profile_background",
                price_points=180,
                preview_value="#6d28d9",
            ),
            dict(
                code="ember_aura",
                name="Ember Aura",
                item_type="aura",
                price_points=160,
                preview_value="#fb923c",
            ),
            dict(
                code="royal_violet_aura",
                name="Royal Violet Aura",
                item_type="aura",
                price_points=350,
                preview_value="#a78bfa",
                is_premium=True,
            ),
            dict(
                code="mythic_gold_frame",
                name="Mythic Gold Frame",
                item_type="profile_frame",
                price_points=450,
                preview_value="#facc15",
                is_premium=True,
            ),
            dict(
                code="arcane_night_background",
                name="Arcane Night Background",
                item_type="profile_background",
                price_points=400,
                preview_value="#312e81",
                is_premium=True,
            ),
        ]
        for cosmetic_data in cosmetics:
            cosmetic = await db.scalar(
                select(CosmeticItem).where(CosmeticItem.code == cosmetic_data["code"])
            )
            if cosmetic is None:
                db.add(CosmeticItem(**cosmetic_data))
            else:
                cosmetic.name = cosmetic_data["name"]
                cosmetic.item_type = cosmetic_data["item_type"]
                cosmetic.price_points = cosmetic_data["price_points"]
                cosmetic.preview_value = cosmetic_data["preview_value"]
                cosmetic.is_premium = cosmetic_data.get("is_premium", False)
                cosmetic.is_active = True

        if (
            await db.scalar(
                select(PvpQuestion).where(PvpQuestion.question.ilike("%FastAPI%"))
            )
            is None
        ):
            db.add_all(
                [
                    PvpQuestion(
                        question="What is FastAPI primarily used for?",
                        option_a="Building Python web APIs",
                        option_b="Editing videos",
                        option_c="Designing 3D models",
                        option_d="Mining cryptocurrency",
                        correct_option="A",
                    ),
                    PvpQuestion(
                        question="Which database is selected for SkillArena?",
                        option_a="SQLite only",
                        option_b="PostgreSQL",
                        option_c="MongoDB only",
                        option_d="Excel",
                        correct_option="B",
                    ),
                ]
            )

        admin = await db.scalar(
            select(User).where(User.steam_id == "76561198000000000")
        )
        if admin:
            admin.role = UserRole.ADMIN

        await db.commit()
        print("Demo data seeded.")


if __name__ == "__main__":
    asyncio.run(main())
