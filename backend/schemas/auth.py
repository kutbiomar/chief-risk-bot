from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


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


class ForgotPasswordResponse(BaseModel):
    accepted: bool


class MessageResponse(BaseModel):
    detail: str
