from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.gamification import CosmeticItem, UserCosmetic
from app.models.user import User
from app.routers.deps import DbSession, require_user
from app.services.analytics import track_event

router = APIRouter(prefix="/shop", tags=["shop"])


def templates(request: Request):
    return request.app.state.templates


async def owned_cosmetics_by_item_id(
    db: DbSession, user_id: int
) -> dict[int, UserCosmetic]:
    owned = (
        (
            await db.execute(
                select(UserCosmetic)
                .where(UserCosmetic.user_id == user_id)
                .options(selectinload(UserCosmetic.item))
            )
        )
        .scalars()
        .all()
    )
    return {owned_item.cosmetic_item_id: owned_item for owned_item in owned}


@router.get("")
async def shop_page(
    request: Request, db: DbSession, user: User = Depends(require_user)
):
    items = (
        (
            await db.execute(
                select(CosmeticItem)
                .where(CosmeticItem.is_active.is_(True))
                .order_by(
                    CosmeticItem.item_type, CosmeticItem.price_points, CosmeticItem.name
                )
            )
        )
        .scalars()
        .all()
    )
    owned_by_item_id = await owned_cosmetics_by_item_id(db, user.id)
    return templates(request).TemplateResponse(
        request,
        "shop.html",
        {
            "request": request,
            "user": user,
            "items": items,
            "owned_by_item_id": owned_by_item_id,
        },
    )


@router.post("/{item_id}/buy")
async def buy_item(item_id: int, db: DbSession, user: User = Depends(require_user)):
    item = await db.get(CosmeticItem, item_id)
    if item is None or not item.is_active:
        return RedirectResponse("/shop?error=item-not-found", status_code=303)

    existing = await db.scalar(
        select(UserCosmetic).where(
            UserCosmetic.user_id == user.id,
            UserCosmetic.cosmetic_item_id == item.id,
        )
    )
    if existing:
        return RedirectResponse("/shop?info=already-owned", status_code=303)

    if user.skill_points < item.price_points:
        return RedirectResponse("/shop?error=not-enough-points", status_code=303)

    user.skill_points -= item.price_points
    db.add(UserCosmetic(user_id=user.id, cosmetic_item_id=item.id, is_equipped=False))
    await track_event(
        db,
        user,
        "shop_purchase",
        "cosmetic",
        item.id,
        {"price_points": item.price_points, "item_type": item.item_type},
    )
    await db.commit()
    return RedirectResponse("/shop?success=purchased", status_code=303)


@router.post("/{item_id}/equip")
async def equip_item(item_id: int, db: DbSession, user: User = Depends(require_user)):
    owned = await db.scalar(
        select(UserCosmetic)
        .where(
            UserCosmetic.user_id == user.id, UserCosmetic.cosmetic_item_id == item_id
        )
        .options(selectinload(UserCosmetic.item))
    )
    if owned is None:
        return RedirectResponse("/shop?error=not-owned", status_code=303)

    same_type_items = (
        (
            await db.execute(
                select(UserCosmetic)
                .join(UserCosmetic.item)
                .where(
                    UserCosmetic.user_id == user.id,
                    CosmeticItem.item_type == owned.item.item_type,
                )
            )
        )
        .scalars()
        .all()
    )
    for cosmetic in same_type_items:
        cosmetic.is_equipped = cosmetic.id == owned.id

    await db.commit()
    return RedirectResponse("/shop?success=equipped", status_code=303)


@router.post("/{item_id}/unequip")
async def unequip_item(item_id: int, db: DbSession, user: User = Depends(require_user)):
    owned = await db.scalar(
        select(UserCosmetic).where(
            UserCosmetic.user_id == user.id,
            UserCosmetic.cosmetic_item_id == item_id,
        )
    )
    if owned:
        owned.is_equipped = False
        await db.commit()
    return RedirectResponse("/shop?success=unequipped", status_code=303)
