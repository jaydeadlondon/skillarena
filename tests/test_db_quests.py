import asyncio

from sqlalchemy import select

from app.models.course import Course, Lesson, LessonProgress
from app.models.gamification import Quest, QuestFrequency, UserQuest
from app.models.user import User
from app.services.quests import claim_quest
from tests.db_helpers import run_with_test_db


def test_claim_completed_daily_quest_once():
    async def scenario(session):
        user = User(steam_id="steam_quest", display_name="Quest Tester", skill_points=0)
        course = Course(
            title="Quest Course",
            slug="quest-course",
            description="Testing quests",
            is_published=True,
        )
        session.add_all([user, course])
        await session.flush()

        lesson = Lesson(
            course_id=course.id,
            title="Quest Lesson",
            position=1,
            video_url="https://www.youtube.com/watch?v=abc123",
            duration_minutes=5,
        )
        session.add(lesson)
        await session.flush()
        session.add(
            LessonProgress(
                user_id=user.id,
                lesson_id=lesson.id,
                completed=True,
                watched_seconds=300,
            )
        )

        quest = Quest(
            title="Complete one lesson test",
            description="Complete one lesson.",
            frequency=QuestFrequency.DAILY,
            target_metric="lessons_completed",
            target_value=1,
            reward_points=25,
        )
        session.add(quest)
        await session.flush()

        success, code = await claim_quest(session, user, quest.id)
        assert success is True
        assert code == "claimed"
        await session.commit()
        await session.refresh(user)

        user_quest = await session.scalar(
            select(UserQuest).where(UserQuest.user_id == user.id)
        )
        assert user.skill_points == 25
        assert user_quest is not None
        assert user_quest.completed is True
        assert user_quest.claimed is True

        success, code = await claim_quest(session, user, quest.id)
        assert success is False
        assert code == "already-claimed"

    asyncio.run(run_with_test_db(scenario))
