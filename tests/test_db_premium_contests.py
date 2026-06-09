import asyncio

from sqlalchemy import select

from app.models.pvp import (
    BattleStatus,
    PvpBattle,
    PvpBattleSubmission,
    PvpContest,
    PvpContestEntry,
    PvpContestStatus,
)
from app.models.user import User
from app.routers.pvp import finish_battle_if_ready
from tests.db_helpers import run_with_test_db


def test_active_contest_entry_score_increases_after_pvp_win():
    async def scenario(session):
        winner = User(
            steam_id="steam_contest_winner",
            display_name="Contest Winner",
            skill_points=100,
            plan="premium",
        )
        loser = User(
            steam_id="steam_contest_loser",
            display_name="Contest Loser",
            skill_points=100,
            plan="premium",
        )
        session.add_all([winner, loser])
        await session.flush()

        contest = PvpContest(
            title="Test Contest", description="Contest", status=PvpContestStatus.ACTIVE
        )
        session.add(contest)
        await session.flush()
        entry = PvpContestEntry(contest_id=contest.id, user_id=winner.id, score=0)
        session.add(entry)

        battle = PvpBattle(
            challenger_id=winner.id,
            opponent_id=loser.id,
            status=BattleStatus.ACTIVE,
            challenger_score=4,
            opponent_score=2,
            entry_fee_points=10,
            reward_points=25,
        )
        session.add(battle)
        await session.flush()
        session.add_all(
            [
                PvpBattleSubmission(
                    battle_id=battle.id, user_id=winner.id, score=4, total_questions=5
                ),
                PvpBattleSubmission(
                    battle_id=battle.id, user_id=loser.id, score=2, total_questions=5
                ),
            ]
        )
        await session.flush()

        await finish_battle_if_ready(session, battle)
        await session.commit()

        updated_entry = await session.scalar(
            select(PvpContestEntry).where(
                PvpContestEntry.contest_id == contest.id,
                PvpContestEntry.user_id == winner.id,
            )
        )
        assert updated_entry.score == 1

    asyncio.run(run_with_test_db(scenario))


def test_inactive_contest_entry_score_does_not_increase():
    async def scenario(session):
        winner = User(
            steam_id="steam_inactive_winner",
            display_name="Inactive Winner",
            skill_points=100,
            plan="premium",
        )
        loser = User(
            steam_id="steam_inactive_loser",
            display_name="Inactive Loser",
            skill_points=100,
            plan="premium",
        )
        session.add_all([winner, loser])
        await session.flush()

        contest = PvpContest(
            title="Finished Contest",
            description="Contest",
            status=PvpContestStatus.FINISHED,
        )
        session.add(contest)
        await session.flush()
        entry = PvpContestEntry(contest_id=contest.id, user_id=winner.id, score=0)
        session.add(entry)

        battle = PvpBattle(
            challenger_id=winner.id,
            opponent_id=loser.id,
            status=BattleStatus.ACTIVE,
            challenger_score=4,
            opponent_score=2,
            entry_fee_points=10,
            reward_points=25,
        )
        session.add(battle)
        await session.flush()
        session.add_all(
            [
                PvpBattleSubmission(
                    battle_id=battle.id, user_id=winner.id, score=4, total_questions=5
                ),
                PvpBattleSubmission(
                    battle_id=battle.id, user_id=loser.id, score=2, total_questions=5
                ),
            ]
        )
        await session.flush()

        await finish_battle_if_ready(session, battle)
        await session.commit()

        updated_entry = await session.scalar(
            select(PvpContestEntry).where(
                PvpContestEntry.contest_id == contest.id,
                PvpContestEntry.user_id == winner.id,
            )
        )
        assert updated_entry.score == 0

    asyncio.run(run_with_test_db(scenario))
