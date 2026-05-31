from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SkillArena"
    app_env: str = "development"
    app_secret_key: str = Field(default="dev-secret-change-before-production")
    app_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://skillarena:skillarena@db:5432/skillarena"

    steam_api_key: str = ""
    steam_realm: str = "http://localhost:8000"
    steam_return_url: str = "http://localhost:8000/auth/steam/callback"
    steam_mock_login: bool = True
    admin_steam_ids: str = ""

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
