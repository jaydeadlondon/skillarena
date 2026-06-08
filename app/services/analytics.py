import json
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analytics import AnalyticsEvent
from app.models.user import User


def _safe_metadata(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return "{}"
    try:
        return json.dumps(metadata, ensure_ascii=False, default=str)[:4000]
    except TypeError:
        return "{}"


async def track_event(
    db: AsyncSession,
    user: User | None,
    event_type: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AnalyticsEvent(
            user_id=user.id if user else None,
            event_type=event_type[:80],
            reference_type=reference_type[:80] if reference_type else None,
            reference_id=reference_id,
            event_metadata=_safe_metadata(metadata),
        )
    )


def start_of_today() -> datetime:
    return datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)


def start_of_days_ago(days: int) -> datetime:
    return start_of_today() - timedelta(days=days - 1)


async def count_events(
    db: AsyncSession, event_type: str | None = None, since: datetime | None = None
) -> int:
    query = select(func.count(AnalyticsEvent.id))
    if event_type:
        query = query.where(AnalyticsEvent.event_type == event_type)
    if since:
        query = query.where(AnalyticsEvent.created_at >= since)
    return int((await db.scalar(query)) or 0)


async def active_users_count(db: AsyncSession, since: datetime) -> int:
    return int(
        (
            await db.scalar(
                select(func.count(distinct(AnalyticsEvent.user_id))).where(
                    AnalyticsEvent.user_id.is_not(None),
                    AnalyticsEvent.created_at >= since,
                )
            )
        )
        or 0
    )


async def recent_events(db: AsyncSession, limit: int = 50) -> list[AnalyticsEvent]:
    return (
        (
            await db.execute(
                select(AnalyticsEvent)
                .options(selectinload(AnalyticsEvent.user))
                .order_by(AnalyticsEvent.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


async def build_admin_analytics(db: AsyncSession) -> dict[str, Any]:
    today = start_of_today()
    week = start_of_days_ago(7)
    tracked = [
        "user_login",
        "lesson_completed",
        "course_completed",
        "quest_claimed",
        "focus_completed",
        "pvp_created",
        "pvp_joined",
        "pvp_finished",
        "shop_purchase",
        "ai_request",
        "ai_quiz_generated",
        "ai_quests_generated",
    ]
    today_counts = {event: await count_events(db, event, today) for event in tracked}
    week_counts = {event: await count_events(db, event, week) for event in tracked}
    return {
        "events_today": await count_events(db, since=today),
        "events_week": await count_events(db, since=week),
        "active_users_today": await active_users_count(db, today),
        "active_users_week": await active_users_count(db, week),
        "today_counts": today_counts,
        "week_counts": week_counts,
        "recent_events": await recent_events(db, 50),
    }
