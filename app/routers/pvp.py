from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.models.pvp import BattleStatus, PvpBattle, PvpQuestion
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.rewards import add_skill_points

router = APIRouter(prefix="/pvp", tags=["pvp"])
ENTRY_FEE = 10
REWARD = 25


def templates(request: Request):
    return request.app.state.templates


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
    questions_count = len(
        (await db.execute(select(PvpQuestion).where(PvpQuestion.is_active.is_(True))))
        .scalars()
        .all()
    )
    return templates(request).TemplateResponse(
        request,
        "pvp.html",
        {
            "request": request,
            "user": user,
            "battles": battles,
            "questions_count": questions_count,
        },
    )


@router.post("/create")
async def create_battle(db: DbSession, user: User = Depends(require_user)):
    if user.skill_points < ENTRY_FEE:
        return RedirectResponse("/pvp?error=not-enough-points", status_code=303)
    user.skill_points -= ENTRY_FEE
    battle = PvpBattle(
        challenger_id=user.id, entry_fee_points=ENTRY_FEE, reward_points=REWARD
    )
    db.add(battle)
    await db.commit()
    return RedirectResponse("/pvp", status_code=303)


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
    await db.commit()
    return RedirectResponse(f"/pvp/{battle.id}/play", status_code=303)


@router.get("/{battle_id}/play")
async def play_battle(
    battle_id: int, request: Request, db: DbSession, user: User = Depends(require_user)
):
    battle = await db.get(PvpBattle, battle_id)
    questions = (
        (
            await db.execute(
                select(PvpQuestion).where(PvpQuestion.is_active.is_(True)).limit(5)
            )
        )
        .scalars()
        .all()
    )
    return templates(request).TemplateResponse(
        request,
        "pvp_play.html",
        {"request": request, "user": user, "battle": battle, "questions": questions},
    )


@router.post("/{battle_id}/submit")
async def submit_battle(
    battle_id: int,
    db: DbSession,
    user: User = Depends(require_user),
    score: int = Form(0),
):
    battle = await db.get(PvpBattle, battle_id)
    if not battle:
        return RedirectResponse("/pvp", status_code=303)

    if battle.challenger_id == user.id:
        battle.challenger_score = score
    elif battle.opponent_id == user.id:
        battle.opponent_score = score

    if battle.opponent_id and battle.challenger_score + battle.opponent_score > 0:
        battle.status = BattleStatus.FINISHED
        if battle.challenger_score >= battle.opponent_score:
            battle.winner_id = battle.challenger_id
        else:
            battle.winner_id = battle.opponent_id
        if battle.winner_id == user.id:
            await add_skill_points(
                db,
                user,
                battle.reward_points + battle.entry_fee_points * 2,
                "PvP battle won",
                "pvp",
                battle.id,
            )

    await db.commit()
    return RedirectResponse("/pvp", status_code=303)
