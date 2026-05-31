from urllib.parse import urljoin

import httpx

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import get_settings
from app.models.user import User
from app.routers.deps import DbSession, user_by_steam_id
from app.services.steam import SteamService, SteamServiceError

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
steam = SteamService()


def _steam_urls_from_request(request: Request) -> tuple[str, str]:
    base_url = str(request.base_url).rstrip("/") + "/"
    realm = base_url.rstrip("/")
    return_to = urljoin(base_url, "auth/steam/callback")
    return realm, return_to


@router.get("/steam")
async def steam_login(request: Request) -> RedirectResponse:
    realm, return_to = _steam_urls_from_request(request)
    return RedirectResponse(steam.build_login_url(realm=realm, return_to=return_to), status_code=303)


@router.get("/steam/login-url")
async def steam_login_url_debug(request: Request) -> JSONResponse:
    """Debug helper: open this route to see the exact Steam URL we generate."""
    realm, return_to = _steam_urls_from_request(request)
    return JSONResponse(
        {
            "realm": realm,
            "return_to": return_to,
            "steam_login_url": steam.build_login_url(realm=realm, return_to=return_to),
        }
    )


@router.get("/steam/mock")
async def mock_steam_login(request: Request, db: DbSession) -> RedirectResponse:
    if not settings.steam_mock_login:
        return RedirectResponse("/", status_code=303)

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
    try:
        callback_params = dict(request.query_params)
        steam_id = await steam.validate_openid_response(callback_params)
        profile = await steam.get_player_summary(steam_id)
        playtime_minutes = await steam.get_recent_playtime_minutes(steam_id)
    except (SteamServiceError, httpx.HTTPError, ValueError) as exc:
        return RedirectResponse(f"/?auth_error={str(exc)}", status_code=303)

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
