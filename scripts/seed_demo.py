import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models.course  # noqa: F401,E402
import app.models.gamification  # noqa: F401,E402
import app.models.pvp  # noqa: F401,E402
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
        existing = await db.scalar(
            select(Course).where(Course.slug == "focus-fundamentals")
        )
        if existing is None:
            course = Course(
                title="Focus Fundamentals",
                slug="focus-fundamentals",
                description="A short starter path for building focus with tiny, ADHD-friendly learning steps.",
                category="Productivity",
                is_published=True,
                reward_points=100,
            )
            db.add(course)
            await db.flush()
            db.add_all(
                [
                    Lesson(
                        course_id=course.id,
                        title="The 5-minute focus ritual",
                        position=1,
                        content="Your quest: remove one distraction and learn for five focused minutes.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=inpok4MKVLM",
                        duration_minutes=5,
                        reward_points=10,
                    ),
                    Lesson(
                        course_id=course.id,
                        title="Break big goals into tiny quests",
                        position=2,
                        content="Your quest: rewrite one big goal as three tiny actions.",
                        video_provider=VideoProvider.YOUTUBE,
                        video_url="https://www.youtube.com/watch?v=arj7oStGLkU",
                        duration_minutes=10,
                        reward_points=15,
                    ),
                ]
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
