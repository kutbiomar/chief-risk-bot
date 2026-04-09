from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ChiefRiskBot"
    environment: str = "development"
    database_url: str = "sqlite:///./backend/runtime/chiefriskbot.db"
    secret_key: str = Field(default="replace-me", min_length=8)
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"
    session_ttl_days: int = 30
    anthropic_api_key: str = Field(default="")
    fred_api_key: str = Field(default="")
    azure_document_intelligence_endpoint: str = Field(default="")
    azure_document_intelligence_key: str = Field(default="")
    scheduler_enabled: bool = False

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_use_default(cls, value: str, info) -> str:
        environment = str(info.data.get("environment", "development")).lower()
        if value == "replace-me" and environment != "development":
            raise ValueError("SECRET_KEY must be set outside development")
        return value

    def allowed_origins_list(self) -> list[str]:
        value = self.allowed_origins
        if value.strip().startswith("[") and value.strip().endswith("]"):
            import json

            parsed = json.loads(value)
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
