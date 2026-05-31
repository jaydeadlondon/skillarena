from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.models.user import User
from app.routers.deps import DbSession, user_by_steam_id
from app.services.steam import SteamService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
steam = SteamService()


@router.get("/steam")
async def steam_login() -> RedirectResponse:
    return RedirectResponse(steam.build_login_url())


@router.get("/steam/mock")
async def mock_steam_login(request: Request, db: DbSession) -> RedirectResponse:
    if not settings.steam_mock_login:
        return RedirectResponse("/")

    steam_id = "76561198000000000"
    user = await user_by_steam_id(db, steam_id)
    if user is None:
        user = User(
            steam_id=steam_id,
            display_name="Mock Steam Knight",
            avatar_url="",
            skill_points=150,
            steam_playtime_2w_minutes=840,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/steam/callback")
async def steam_callback(request: Request, db: DbSession) -> RedirectResponse:
    callback_params = dict(request.query_params)
    steam_id = await steam.validate_openid_response(callback_params)
    profile = await steam.get_player_summary(steam_id)
    playtime_minutes = await steam.get_recent_playtime_minutes(steam_id)

    user = await user_by_steam_id(db, steam_id)
    if user is None:
        user = User(
            steam_id=steam_id,
            display_name=profile.get("personaname", "Steam Adventurer"),
            avatar_url=profile.get("avatarfull", ""),
            steam_playtime_2w_minutes=playtime_minutes,
        )
        db.add(user)
    else:
        user.display_name = profile.get("personaname", user.display_name)
        user.avatar_url = profile.get("avatarfull", user.avatar_url)
        user.steam_playtime_2w_minutes = playtime_minutes

    await db.commit()
    await db.refresh(user)
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/", status_code=303)
