import asyncio

from app.models.user import User
from app.services.analytics import (
    active_users_count,
    build_admin_analytics,
    start_of_today,
    track_event,
)
from tests.db_helpers import run_with_test_db


def test_track_event_and_admin_analytics_counts():
    async def scenario(session):
        user = User(steam_id="steam_analytics", display_name="Analytics Tester")
        session.add(user)
        await session.flush()

        await track_event(
            session, user, "lesson_completed", "lesson", 1, {"reward_points": 10}
        )
        await track_event(
            session, user, "ai_request", "lesson", 1, {"prompt_type": "explain"}
        )
        await session.commit()

        analytics = await build_admin_analytics(session)
        assert analytics["events_today"] == 2
        assert analytics["events_week"] == 2
        assert analytics["active_users_today"] == 1
        assert analytics["today_counts"]["lesson_completed"] == 1
        assert analytics["today_counts"]["ai_request"] == 1
        assert len(analytics["recent_events"]) == 2

    asyncio.run(run_with_test_db(scenario))


def test_active_users_counts_distinct_users():
    async def scenario(session):
        user = User(
            steam_id="steam_analytics_distinct", display_name="Analytics Distinct"
        )
        session.add(user)
        await session.flush()
        await track_event(session, user, "lesson_completed", "lesson", 1)
        await track_event(session, user, "quest_claimed", "quest", 1)
        await session.commit()

        assert await active_users_count(session, start_of_today()) == 1

    asyncio.run(run_with_test_db(scenario))
