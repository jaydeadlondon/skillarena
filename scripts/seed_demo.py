import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.course import Course, Lesson, VideoProvider
from app.models.gamification import (
    Achievement,
    AchievementType,
    CosmeticItem,
    Quest,
    QuestFrequency,
)
from app.models.pvp import PvpQuestion
from app.models.user import User, UserRole


async def main() -> None:
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

        if (
            await db.scalar(select(Quest).where(Quest.title == "Study for 20 minutes"))
            is None
        ):
            db.add_all(
                [
                    Quest(
                        title="Study for 20 minutes",
                        description="Open lessons and collect at least 20 minutes of study time today.",
                        frequency=QuestFrequency.DAILY,
                        target_metric="study_minutes",
                        target_value=20,
                        reward_points=25,
                    ),
                    Quest(
                        title="Win one quiz duel",
                        description="Challenge another learner and win a PvP quiz battle.",
                        frequency=QuestFrequency.DAILY,
                        target_metric="pvp_wins",
                        target_value=1,
                        reward_points=40,
                    ),
                ]
            )

        if (
            await db.scalar(
                select(Achievement).where(Achievement.code == "first_lesson")
            )
            is None
        ):
            db.add_all(
                [
                    Achievement(
                        code="first_lesson",
                        title="First Spark",
                        description="Complete your first lesson.",
                        achievement_type=AchievementType.LESSONS,
                        threshold=1,
                        reward_points=10,
                        badge_icon="✨",
                    ),
                    Achievement(
                        code="seven_day_streak",
                        title="Flame Keeper",
                        description="Keep a 7-day learning streak.",
                        achievement_type=AchievementType.STREAK,
                        threshold=7,
                        reward_points=70,
                        badge_icon="🔥",
                    ),
                    Achievement(
                        code="study_over_steam",
                        title="Balance Breaker",
                        description="Study more than you play on Steam over two weeks.",
                        achievement_type=AchievementType.BALANCE,
                        threshold=1,
                        reward_points=100,
                        badge_icon="⚖️",
                    ),
                ]
            )

        if (
            await db.scalar(
                select(CosmeticItem).where(CosmeticItem.code == "violet_aura")
            )
            is None
        ):
            db.add_all(
                [
                    CosmeticItem(
                        code="violet_aura",
                        name="Violet Aura",
                        item_type="profile_background",
                        price_points=120,
                        preview_value="#6d28d9",
                    ),
                    CosmeticItem(
                        code="gold_frame",
                        name="Golden Frame",
                        item_type="profile_frame",
                        price_points=200,
                        preview_value="#f7c948",
                    ),
                ]
            )

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
