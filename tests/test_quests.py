from datetime import date

from app.models.gamification import QuestFrequency
from app.services.quests import (
    daily_period_key,
    period_key_for_frequency,
    week_start,
    weekly_period_key,
)


def test_daily_period_key():
    assert daily_period_key(date(2026, 6, 3)) == "2026-06-03"


def test_week_start_monday():
    assert week_start(date(2026, 6, 3)) == date(2026, 6, 1)


def test_weekly_period_key():
    assert weekly_period_key(date(2026, 6, 3)) == "2026-W23"


def test_period_key_for_frequency():
    assert (
        period_key_for_frequency(QuestFrequency.DAILY, date(2026, 6, 3)) == "2026-06-03"
    )
    assert (
        period_key_for_frequency(QuestFrequency.WEEKLY, date(2026, 6, 3)) == "2026-W23"
    )
