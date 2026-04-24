from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    workspace_name: str
    display_name: str
    email: str
    password: str
    timezone: str = "UTC"
    reporting_currency: str = "CHF"

    @field_validator("workspace_name", "display_name", "email", "timezone", "reporting_currency")
    @classmethod
    def required_string(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Field is required")
        return text

    @field_validator("password")
    @classmethod
    def register_password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        return value


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TotpVerifyRequest(BaseModel):
    session_challenge: str
    code: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    workspace_id: str
    workspace_name: Optional[str] = None


class SessionResponse(BaseModel):
    user: UserResponse


class LoginResponse(BaseModel):
    requires_totp: bool = False
    session_challenge: Optional[str] = None
    user: Optional[UserResponse] = None
    access_token: Optional[str] = None


class ForgotPasswordResponse(BaseModel):
    accepted: bool


class MessageResponse(BaseModel):
    detail: str
