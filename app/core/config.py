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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
