from fastapi import APIRouter, Depends, Request

from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.leaderboards import build_leaderboards

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def leaderboard_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    boards = await build_leaderboards(db)
    return templates(request).TemplateResponse(
        request,
        "leaderboard.html",
        {"request": request, "user": user, "boards": boards},
    )
