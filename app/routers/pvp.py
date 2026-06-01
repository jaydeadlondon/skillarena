from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.pvp import (
    BattleStatus,
    PvpBattle,
    PvpBattleAnswer,
    PvpBattleQuestion,
    PvpBattleSubmission,
    PvpQuestion,
)
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.achievements import evaluate_pvp_achievements
from app.services.rewards import add_skill_points
from app.services.streaks import sync_user_streak

router = APIRouter(prefix="/pvp", tags=["pvp"])
ENTRY_FEE = 10
REWARD = 25
QUESTIONS_PER_BATTLE = 5


def templates(request: Request):
    return request.app.state.templates


async def ensure_battle_questions(
    db: DbSession, battle: PvpBattle
) -> list[PvpQuestion]:
    existing_links = (
        (
            await db.execute(
                select(PvpBattleQuestion)
                .where(PvpBattleQuestion.battle_id == battle.id)
                .options(selectinload(PvpBattleQuestion.question))
                .order_by(PvpBattleQuestion.position)
            )
        )
        .scalars()
        .all()
    )
    if existing_links:
        return [link.question for link in existing_links]

    questions = (
        (
            await db.execute(
                select(PvpQuestion)
                .where(PvpQuestion.is_active.is_(True))
                .order_by(func.random())
                .limit(QUESTIONS_PER_BATTLE)
            )
        )
        .scalars()
        .all()
    )

    for index, question in enumerate(questions, start=1):
        db.add(
            PvpBattleQuestion(
                battle_id=battle.id, question_id=question.id, position=index
            )
        )
    await db.flush()
    return questions


async def get_user_submission(
    db: DbSession, battle_id: int, user_id: int
) -> PvpBattleSubmission | None:
    return (
        await db.execute(
            select(PvpBattleSubmission)
            .where(
                PvpBattleSubmission.battle_id == battle_id,
                PvpBattleSubmission.user_id == user_id,
            )
            .options(
                selectinload(PvpBattleSubmission.answers).selectinload(
                    PvpBattleAnswer.question
                )
            )
        )
    ).scalar_one_or_none()


async def finish_battle_if_ready(db: DbSession, battle: PvpBattle) -> None:
    if not battle.opponent_id or battle.status == BattleStatus.FINISHED:
        return

    submissions = (
        (
            await db.execute(
                select(PvpBattleSubmission).where(
                    PvpBattleSubmission.battle_id == battle.id
                )
            )
        )
        .scalars()
        .all()
    )
    submitted_user_ids = {submission.user_id for submission in submissions}
    required_user_ids = {battle.challenger_id, battle.opponent_id}
    if not required_user_ids.issubset(submitted_user_ids):
        return

    battle.status = BattleStatus.FINISHED
    if battle.challenger_score >= battle.opponent_score:
        battle.winner_id = battle.challenger_id
    else:
        battle.winner_id = battle.opponent_id

    winner = await db.get(User, battle.winner_id)
    if winner:
        prize = battle.reward_points + battle.entry_fee_points * 2
        await add_skill_points(db, winner, prize, "PvP battle won", "pvp", battle.id)
        await evaluate_pvp_achievements(db, winner)

    challenger = await db.get(User, battle.challenger_id)
    if challenger:
        await evaluate_pvp_achievements(db, challenger)
        await sync_user_streak(db, challenger)
    if battle.opponent_id:
        opponent = await db.get(User, battle.opponent_id)
        if opponent:
            await evaluate_pvp_achievements(db, opponent)
            await sync_user_streak(db, opponent)


@router.get("")
async def pvp_lobby(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    battles = (
        (
            await db.execute(
                select(PvpBattle).order_by(PvpBattle.created_at.desc()).limit(20)
            )
        )
        .scalars()
        .all()
    )
    questions_count = await db.scalar(
        select(func.count(PvpQuestion.id)).where(PvpQuestion.is_active.is_(True))
    )
    return templates(request).TemplateResponse(
        request,
        "pvp.html",
        {
            "request": request,
            "user": user,
            "battles": battles,
            "questions_count": questions_count or 0,
            "entry_fee": ENTRY_FEE,
        },
    )


@router.post("/create")
async def create_battle(db: DbSession, user: User = Depends(require_user)):
    active_questions_count = await db.scalar(
        select(func.count(PvpQuestion.id)).where(PvpQuestion.is_active.is_(True))
    )
    if not active_questions_count:
        return RedirectResponse("/pvp?error=no-questions", status_code=303)
    if user.skill_points < ENTRY_FEE:
        return RedirectResponse("/pvp?error=not-enough-points", status_code=303)

    user.skill_points -= ENTRY_FEE
    battle = PvpBattle(
        challenger_id=user.id, entry_fee_points=ENTRY_FEE, reward_points=REWARD
    )
    db.add(battle)
    await db.flush()
    await ensure_battle_questions(db, battle)
    await db.commit()
    return RedirectResponse(f"/pvp/{battle.id}/play", status_code=303)


@router.post("/{battle_id}/join")
async def join_battle(
    battle_id: int, db: DbSession, user: User = Depends(require_user)
):
    battle = await db.get(PvpBattle, battle_id)
    if (
        not battle
        or battle.status != BattleStatus.WAITING
        or battle.challenger_id == user.id
    ):
        return RedirectResponse("/pvp", status_code=303)
    if user.skill_points < battle.entry_fee_points:
        return RedirectResponse("/pvp?error=not-enough-points", status_code=303)

    user.skill_points -= battle.entry_fee_points
    battle.opponent_id = user.id
    battle.status = BattleStatus.ACTIVE
    await ensure_battle_questions(db, battle)
    await db.commit()
    return RedirectResponse(f"/pvp/{battle.id}/play", status_code=303)


@router.get("/{battle_id}/play")
async def play_battle(
    battle_id: int, request: Request, db: DbSession, user: User = Depends(require_user)
):
    battle = await db.get(PvpBattle, battle_id)
    if not battle or user.id not in {battle.challenger_id, battle.opponent_id}:
        return RedirectResponse("/pvp", status_code=303)

    questions = await ensure_battle_questions(db, battle)
    submission = await get_user_submission(db, battle.id, user.id)
    opponent_submission = None
    if battle.opponent_id:
        opponent_id = (
            battle.opponent_id
            if user.id == battle.challenger_id
            else battle.challenger_id
        )
        opponent_submission = await get_user_submission(db, battle.id, opponent_id)

    await db.commit()
    return templates(request).TemplateResponse(
        request,
        "pvp_play.html",
        {
            "request": request,
            "user": user,
            "battle": battle,
            "questions": questions,
            "submission": submission,
            "opponent_submission": opponent_submission,
        },
    )


@router.post("/{battle_id}/submit")
async def submit_battle(
    battle_id: int,
    request: Request,
    db: DbSession,
    user: User = Depends(require_user),
):
    battle = await db.get(PvpBattle, battle_id)
    if not battle or user.id not in {battle.challenger_id, battle.opponent_id}:
        return RedirectResponse("/pvp", status_code=303)
    if battle.status == BattleStatus.FINISHED:
        return RedirectResponse(f"/pvp/{battle.id}/play", status_code=303)

    existing_submission = await get_user_submission(db, battle.id, user.id)
    if existing_submission:
        return RedirectResponse(f"/pvp/{battle.id}/play", status_code=303)

    form = await request.form()
    questions = await ensure_battle_questions(db, battle)
    score = 0
    submission = PvpBattleSubmission(
        battle_id=battle.id,
        user_id=user.id,
        score=0,
        total_questions=len(questions),
    )
    db.add(submission)
    await db.flush()

    for question in questions:
        selected = str(form.get(f"question_{question.id}", "")).upper()[:1]
        if selected not in {"A", "B", "C", "D"}:
            selected = "-"
        correct = question.correct_option.upper()[:1]
        is_correct = selected == correct
        if is_correct:
            score += 1
        db.add(
            PvpBattleAnswer(
                submission_id=submission.id,
                question_id=question.id,
                selected_option=selected,
                correct_option=correct,
                is_correct=is_correct,
            )
        )

    submission.score = score
    if battle.challenger_id == user.id:
        battle.challenger_score = score
    else:
        battle.opponent_score = score

    await finish_battle_if_ready(db, battle)
    await db.commit()
    return RedirectResponse(f"/pvp/{battle.id}/play", status_code=303)
