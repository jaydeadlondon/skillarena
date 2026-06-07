import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.course import Course, Lesson, LessonProgress
from app.models.user import CurrencyTransaction, User
from app.services.course_progress import maybe_award_course_completion
from tests.db_helpers import run_with_test_db


def test_course_completion_reward_is_awarded_once():
    async def scenario(session):
        user = User(
            steam_id="steam_course", display_name="Course Tester", skill_points=0
        )
        course = Course(
            title="Course Reward",
            slug="course-reward",
            description="Testing course reward",
            is_published=True,
            reward_points=100,
        )
        session.add_all([user, course])
        await session.flush()

        lesson_1 = Lesson(
            course_id=course.id,
            title="Lesson 1",
            position=1,
            video_url="https://www.youtube.com/watch?v=abc123",
            duration_minutes=5,
        )
        lesson_2 = Lesson(
            course_id=course.id,
            title="Lesson 2",
            position=2,
            video_url="https://www.youtube.com/watch?v=def456",
            duration_minutes=5,
        )
        session.add_all([lesson_1, lesson_2])
        await session.flush()
        session.add_all(
            [
                LessonProgress(
                    user_id=user.id,
                    lesson_id=lesson_1.id,
                    completed=True,
                    watched_seconds=300,
                ),
                LessonProgress(
                    user_id=user.id,
                    lesson_id=lesson_2.id,
                    completed=True,
                    watched_seconds=300,
                ),
            ]
        )
        await session.commit()

        loaded_course = await session.scalar(
            select(Course)
            .where(Course.id == course.id)
            .options(selectinload(Course.lessons))
        )
        loaded_user = await session.get(User, user.id)

        first_award = await maybe_award_course_completion(
            session, loaded_user, loaded_course
        )
        await session.commit()
        await session.refresh(loaded_user)
        second_award = await maybe_award_course_completion(
            session, loaded_user, loaded_course
        )
        await session.commit()

        transactions = (
            (
                await session.execute(
                    select(CurrencyTransaction).where(
                        CurrencyTransaction.user_id == user.id,
                        CurrencyTransaction.reference_type == "course",
                        CurrencyTransaction.reference_id == course.id,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert first_award is True
        assert second_award is False
        assert loaded_user.skill_points == 100
        assert len(transactions) == 1
        assert transactions[0].reason == "Course completed"

    asyncio.run(run_with_test_db(scenario))
