import re
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
STEAM_PLAYER_SUMMARIES_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
STEAM_RECENTLY_PLAYED_URL = "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/"
STEAM_ID_RE = re.compile(r"https://steamcommunity.com/openid/id/(\d+)")


class SteamServiceError(RuntimeError):
    pass


class SteamService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_login_url(self, realm: str | None = None, return_to: str | None = None) -> str:
        """Build Steam OpenID login URL.

        `realm` and `return_to` can be passed from the current request. This is
        important in local development because Steam is strict about callback
        URLs and users may open the app as localhost, 127.0.0.1, or a LAN host.
        """
        params = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.mode": "checkid_setup",
            "openid.return_to": return_to or self.settings.steam_return_url,
            "openid.realm": realm or self.settings.steam_realm,
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        }
        return f"{STEAM_OPENID_URL}?{urlencode(params)}"

    async def validate_openid_response(self, callback_params: dict[str, str]) -> str:
        verification_payload = dict(callback_params)
        verification_payload["openid.mode"] = "check_authentication"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(STEAM_OPENID_URL, data=verification_payload)
        response.raise_for_status()

        if "is_valid:true" not in response.text:
            raise SteamServiceError("Steam OpenID response is not valid.")

        claimed_id = callback_params.get("openid.claimed_id", "")
        match = STEAM_ID_RE.fullmatch(claimed_id)
        if not match:
            raise SteamServiceError("Could not extract Steam ID from OpenID response.")
        return match.group(1)

    async def get_player_summary(self, steam_id: str) -> dict:
        if not self.settings.steam_api_key or self.settings.steam_api_key.startswith("put-"):
            return {
                "steamid": steam_id,
                "personaname": f"Steam Hero {steam_id[-4:]}",
                "avatarfull": "",
            }

        params = {"key": self.settings.steam_api_key, "steamids": steam_id}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(STEAM_PLAYER_SUMMARIES_URL, params=params)
        response.raise_for_status()
        players = response.json().get("response", {}).get("players", [])
        if not players:
            raise SteamServiceError("Steam profile was not found.")
        return players[0]

    async def get_recent_playtime_minutes(self, steam_id: str) -> int:
        if not self.settings.steam_api_key or self.settings.steam_api_key.startswith("put-"):
            return 840

        params = {"key": self.settings.steam_api_key, "steamid": steam_id, "format": "json"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(STEAM_RECENTLY_PLAYED_URL, params=params)
        response.raise_for_status()
        games = response.json().get("response", {}).get("games", [])
        return sum(int(game.get("playtime_2weeks", 0)) for game in games)
