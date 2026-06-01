from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.quests import claim_daily_quest, get_daily_quest_cards

router = APIRouter(prefix="/quests", tags=["quests"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def quests_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    quest_cards = await get_daily_quest_cards(db, user)
    await db.commit()
    completed_count = sum(1 for card in quest_cards if card["user_quest"].completed)
    claimed_count = sum(1 for card in quest_cards if card["user_quest"].claimed)
    return templates(request).TemplateResponse(
        request,
        "quests.html",
        {
            "request": request,
            "user": user,
            "quest_cards": quest_cards,
            "completed_count": completed_count,
            "claimed_count": claimed_count,
        },
    )


@router.post("/{quest_id}/claim")
async def claim_quest(quest_id: int, db: DbSession, user: User = Depends(require_user)):
    success, code = await claim_daily_quest(db, user, quest_id)
    await db.commit()
    if success:
        return RedirectResponse("/quests?success=claimed", status_code=303)
    return RedirectResponse(f"/quests?error={code}", status_code=303)
