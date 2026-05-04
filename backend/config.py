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
    auth_mode: str = "local"
    anthropic_api_key: str = Field(default="")
    ai_generation_enabled: bool = True
    anthropic_daily_token_cap: int = 0
    briefing_daily_quota: int = 5
    document_upload_max_bytes: int = 25 * 1024 * 1024
    fred_api_key: str = Field(default="")
    azure_document_intelligence_endpoint: str = Field(default="")
    azure_document_intelligence_key: str = Field(default="")
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_role_key: str = Field(default="")
    supabase_storage_bucket: str = Field(default="documents")
    scheduler_enabled: bool = False
    sentry_dsn: str = Field(default="")
    observability_synthetic_errors_enabled: bool = False

    @field_validator("auth_mode")
    @classmethod
    def auth_mode_must_be_supported(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local", "supabase"}:
            raise ValueError("AUTH_MODE must be 'local' or 'supabase'")
        return normalized

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

    def validate_runtime(self) -> None:
        origins = self.allowed_origins_list()
        if self.environment.lower() != "development" and any(origin == "*" for origin in origins):
            raise ValueError("ALLOWED_ORIGINS cannot contain '*' outside development")
        if self.environment.lower() == "production":
            insecure = [origin for origin in origins if origin.startswith("http://") and "localhost" not in origin]
            if insecure:
                raise ValueError("ALLOWED_ORIGINS must use https:// in production")

        if self.auth_mode == "supabase":
            missing = []
            if not self.supabase_url:
                missing.append("SUPABASE_URL")
            if not self.supabase_anon_key:
                missing.append("SUPABASE_ANON_KEY")
            if not self.supabase_service_role_key:
                missing.append("SUPABASE_SERVICE_ROLE_KEY")
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"Supabase auth mode requires: {joined}")

    def normalized_database_url(self) -> str:
        value = self.database_url.strip()
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
