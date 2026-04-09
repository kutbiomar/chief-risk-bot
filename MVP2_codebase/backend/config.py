from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ChiefRiskBot MVP2"
    environment: str = "development"
    database_url: str = "sqlite:///./MVP2_codebase/backend/runtime/mvp2.db"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )
    session_ttl_days: int = 30
    allow_dev_auth_headers: bool = False
    demo_workspace_id: str = "demo-workspace"
    demo_user_id: str = "demo-user"
    demo_user_email: str = "auth@example.com"
    demo_user_password: str = "secret123"

    supabase_url: str = ""
    supabase_key: str = ""
    anthropic_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    document_storage_backend: str = "local"
    reconciliation_variance_threshold_pct: float = 2.0
    capital_call_alert_days: int = 14
    scheduler_enabled: bool = False
    liquidity_buffer_default: float = 0.0
    base_currency_default: str = "USD"


@lru_cache
def get_settings() -> Settings:
    return Settings()
