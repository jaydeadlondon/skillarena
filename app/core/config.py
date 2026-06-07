from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SkillArena"
    app_version: str = "0.9.0"
    app_env: str = "development"
    app_secret_key: str = Field(default="dev-secret-change-before-production")
    app_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://skillarena:skillarena@db:5432/skillarena"

    steam_api_key: str = ""
    steam_realm: str = "http://localhost:8000"
    steam_return_url: str = "http://localhost:8000/auth/steam/callback"
    steam_mock_login: bool = True
    admin_steam_ids: str = ""

    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_max_age_seconds: int = 60 * 60 * 24 * 14

    llm_enabled: bool = False
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_daily_limit_per_user: int = 20
    llm_cooldown_seconds: int = 8
    llm_max_custom_prompt_chars: int = 700
    llm_timeout_seconds: int = 30

    pvp_create_cooldown_seconds: int = 20
    pvp_max_waiting_battles_per_user: int = 3

    trusted_hosts: str = "localhost,127.0.0.1,0.0.0.0,testserver"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def admin_steam_id_set(self) -> set[str]:
        return {
            steam_id.strip()
            for steam_id in self.admin_steam_ids.split(",")
            if steam_id.strip()
        }

    @property
    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
