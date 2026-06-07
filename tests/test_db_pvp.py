import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.pvp import BattleStatus, PvpBattle, PvpBattleSubmission
from app.models.user import CurrencyTransaction, User
from app.routers.pvp import finish_battle_if_ready
from tests.db_helpers import run_with_test_db


def test_pvp_winner_gets_prize_after_both_submissions():
    async def scenario(session):
        challenger = User(
            steam_id="steam_pvp_winner_1", display_name="Winner", skill_points=90
        )
        opponent = User(
            steam_id="steam_pvp_winner_2", display_name="Loser", skill_points=90
        )
        session.add_all([challenger, opponent])
        await session.flush()

        battle = PvpBattle(
            challenger_id=challenger.id,
            opponent_id=opponent.id,
            status=BattleStatus.ACTIVE,
            entry_fee_points=10,
            reward_points=25,
            challenger_score=3,
            opponent_score=2,
        )
        session.add(battle)
        await session.flush()
        session.add_all(
            [
                PvpBattleSubmission(
                    battle_id=battle.id,
                    user_id=challenger.id,
                    score=3,
                    total_questions=5,
                ),
                PvpBattleSubmission(
                    battle_id=battle.id,
                    user_id=opponent.id,
                    score=2,
                    total_questions=5,
                ),
            ]
        )
        await session.flush()

        await finish_battle_if_ready(session, battle)
        await session.commit()
        await session.refresh(challenger)
        await session.refresh(opponent)
        await session.refresh(battle)

        transaction = await session.scalar(
            select(CurrencyTransaction).where(
                CurrencyTransaction.user_id == challenger.id,
                CurrencyTransaction.reason == "PvP battle won",
            )
        )

        assert battle.status == BattleStatus.FINISHED
        assert battle.winner_id == challenger.id
        assert challenger.skill_points == 135  # 90 + reward 25 + both entry fees 20
        assert opponent.skill_points == 90
        assert transaction is not None
        assert transaction.amount == 45

    asyncio.run(run_with_test_db(scenario))


def test_pvp_tie_refunds_entry_fee_to_both_players():
    async def scenario(session):
        challenger = User(
            steam_id="steam_pvp_tie_1", display_name="Tie One", skill_points=90
        )
        opponent = User(
            steam_id="steam_pvp_tie_2", display_name="Tie Two", skill_points=90
        )
        session.add_all([challenger, opponent])
        await session.flush()

        battle = PvpBattle(
            challenger_id=challenger.id,
            opponent_id=opponent.id,
            status=BattleStatus.ACTIVE,
            entry_fee_points=10,
            reward_points=25,
            challenger_score=2,
            opponent_score=2,
        )
        session.add(battle)
        await session.flush()
        session.add_all(
            [
                PvpBattleSubmission(
                    battle_id=battle.id,
                    user_id=challenger.id,
                    score=2,
                    total_questions=5,
                ),
                PvpBattleSubmission(
                    battle_id=battle.id,
                    user_id=opponent.id,
                    score=2,
                    total_questions=5,
                ),
            ]
        )
        await session.flush()

        await finish_battle_if_ready(session, battle)
        await session.commit()
        await session.refresh(challenger)
        await session.refresh(opponent)
        await session.refresh(battle)

        refund_transactions = (
            (
                await session.execute(
                    select(CurrencyTransaction).where(
                        CurrencyTransaction.reason == "PvP tie refund"
                    )
                )
            )
            .scalars()
            .all()
        )

        assert battle.status == BattleStatus.FINISHED
        assert battle.winner_id is None
        assert challenger.skill_points == 100
        assert opponent.skill_points == 100
        assert len(refund_transactions) == 2
        assert sorted(transaction.amount for transaction in refund_transactions) == [
            10,
            10,
        ]

    asyncio.run(run_with_test_db(scenario))


def test_pvp_battle_requires_both_submissions_before_finish():
    async def scenario(session):
        challenger = User(
            steam_id="steam_pvp_wait_1", display_name="Wait One", skill_points=90
        )
        opponent = User(
            steam_id="steam_pvp_wait_2", display_name="Wait Two", skill_points=90
        )
        session.add_all([challenger, opponent])
        await session.flush()

        battle = PvpBattle(
            challenger_id=challenger.id,
            opponent_id=opponent.id,
            status=BattleStatus.ACTIVE,
            entry_fee_points=10,
            reward_points=25,
            challenger_score=3,
            opponent_score=0,
        )
        session.add(battle)
        await session.flush()
        session.add(
            PvpBattleSubmission(
                battle_id=battle.id,
                user_id=challenger.id,
                score=3,
                total_questions=5,
            )
        )
        await session.flush()

        await finish_battle_if_ready(session, battle)
        await session.commit()
        await session.refresh(battle)
        await session.refresh(challenger)

        assert battle.status == BattleStatus.ACTIVE
        assert battle.winner_id is None
        assert challenger.skill_points == 90

    asyncio.run(run_with_test_db(scenario))


def test_pvp_duplicate_submission_is_rejected_by_unique_constraint():
    async def scenario(session):
        user = User(
            steam_id="steam_pvp_duplicate", display_name="Duplicate", skill_points=100
        )
        opponent = User(
            steam_id="steam_pvp_duplicate_opponent",
            display_name="Opponent",
            skill_points=100,
        )
        session.add_all([user, opponent])
        await session.flush()

        battle = PvpBattle(
            challenger_id=user.id,
            opponent_id=opponent.id,
            status=BattleStatus.ACTIVE,
        )
        session.add(battle)
        await session.flush()
        session.add_all(
            [
                PvpBattleSubmission(
                    battle_id=battle.id, user_id=user.id, score=1, total_questions=5
                ),
                PvpBattleSubmission(
                    battle_id=battle.id, user_id=user.id, score=2, total_questions=5
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    asyncio.run(run_with_test_db(scenario))
