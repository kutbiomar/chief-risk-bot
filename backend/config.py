from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ChiefRiskBot"
    environment: str = "development"
    database_url: str = "sqlite:///./chiefriskbot.db"
    secret_key: str = Field(default="replace-me", min_length=8)
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )
    session_ttl_days: int = 30
    anthropic_api_key: str = Field(default="")
    fred_api_key: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    return Settings()
