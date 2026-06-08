from fastapi import APIRouter, Depends, Request

from app.models.user import User
from app.routers.deps import require_user
from app.services.plans import is_premium

router = APIRouter(prefix="/premium", tags=["premium"])


def templates(request: Request):
    return request.app.state.templates


@router.get("")
async def premium_page(request: Request, user: User = Depends(require_user)):
    return templates(request).TemplateResponse(
        request,
        "premium.html",
        {"request": request, "user": user, "is_premium_user": is_premium(user)},
    )
