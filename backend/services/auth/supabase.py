from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.config import get_settings


@dataclass
class SupabaseIdentity:
    subject: str
    email: str
    display_name: str


def is_supabase_auth_enabled() -> bool:
    settings = get_settings()
    return settings.auth_mode.lower() == "supabase" and bool(settings.supabase_url and settings.supabase_anon_key)


def _supabase_admin_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


def _identity_from_payload(payload: dict) -> SupabaseIdentity:
    return SupabaseIdentity(
        subject=str(payload["id"]),
        email=str(payload["email"]),
        display_name=str((payload.get("user_metadata") or {}).get("display_name") or payload.get("email", "")),
    )


def _request_json(request: Request, *, timeout: int = 10) -> dict:
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_supabase_user_by_email(email: str) -> Optional[dict]:
    settings = get_settings()
    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users?{urlencode({'page': 1, 'per_page': 200})}",
        headers=_supabase_admin_headers(),
        method="GET",
    )
    try:
        payload = _request_json(request)
    except (HTTPError, URLError):
        return None

    for user in payload.get("users") or []:
        if str(user.get("email", "")).lower() == email.lower():
            return user
    return None


def authenticate_supabase_password(*, email: str, password: str) -> tuple[str, SupabaseIdentity]:
    settings = get_settings()
    if not is_supabase_auth_enabled():
        raise RuntimeError("Supabase auth is not enabled")

    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
        data=json.dumps({"email": email, "password": password}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "apikey": settings.supabase_anon_key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(detail or "Invalid credentials") from exc
    except URLError as exc:
        raise RuntimeError("Unable to reach Supabase Auth") from exc

    access_token = str(payload.get("access_token") or "")
    user = payload.get("user") or {}
    if not access_token or not user.get("id") or not user.get("email"):
        raise ValueError("Invalid Supabase login response")

    return access_token, _identity_from_payload(user)


def _is_invalid_session_error(exc: HTTPError) -> bool:
    return exc.code in {400, 401, 403}


def resolve_supabase_identity(access_token: str) -> Optional[SupabaseIdentity]:
    settings = get_settings()
    if not is_supabase_auth_enabled():
        return None

    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if _is_invalid_session_error(exc):
            return None
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or "Unable to validate Supabase session") from exc
    except URLError as exc:
        raise RuntimeError("Unable to reach Supabase Auth") from exc

    subject = payload.get("id")
    email = payload.get("email")
    if not subject or not email:
        return None

    metadata = payload.get("user_metadata") or {}
    return SupabaseIdentity(subject=str(subject), email=str(email), display_name=str(metadata.get("display_name") or email))


def upsert_supabase_password_user(*, email: str, password: str, display_name: str, email_confirm: bool = True) -> SupabaseIdentity:
    settings = get_settings()
    if not (settings.auth_mode.lower() == "supabase" and settings.supabase_url and settings.supabase_service_role_key):
        raise RuntimeError("Supabase admin provisioning is not enabled")

    existing = _find_supabase_user_by_email(email)
    payload = {
        "email": email,
        "password": password,
        "email_confirm": email_confirm,
        "user_metadata": {"display_name": display_name},
    }

    if existing is None:
        request = Request(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
            data=json.dumps(payload).encode("utf-8"),
            headers=_supabase_admin_headers(),
            method="POST",
        )
    else:
        request = Request(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{existing['id']}",
            data=json.dumps(payload).encode("utf-8"),
            headers=_supabase_admin_headers(),
            method="PUT",
        )

    try:
        response_payload = _request_json(request)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(detail or "Unable to provision Supabase auth user") from exc
    except URLError as exc:
        raise RuntimeError("Unable to reach Supabase Auth admin API") from exc

    if not response_payload.get("id") or not response_payload.get("email"):
        raise ValueError("Invalid Supabase admin response while provisioning user")
    return _identity_from_payload(response_payload)


def create_supabase_password_user(*, email: str, password: str, display_name: str, email_confirm: bool = True) -> SupabaseIdentity:
    settings = get_settings()
    if not (settings.auth_mode.lower() == "supabase" and settings.supabase_url and settings.supabase_service_role_key):
        raise RuntimeError("Supabase admin provisioning is not enabled")

    existing = _find_supabase_user_by_email(email)
    if existing is not None:
        raise ValueError("User already exists in Supabase Auth")

    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users",
        data=json.dumps(
            {
                "email": email,
                "password": password,
                "email_confirm": email_confirm,
                "user_metadata": {"display_name": display_name},
            }
        ).encode("utf-8"),
        headers=_supabase_admin_headers(),
        method="POST",
    )

    try:
        response_payload = _request_json(request)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(detail or "Unable to provision Supabase auth user") from exc
    except URLError as exc:
        raise RuntimeError("Unable to reach Supabase Auth admin API") from exc

    if not response_payload.get("id") or not response_payload.get("email"):
        raise ValueError("Invalid Supabase admin response while provisioning user")
    return _identity_from_payload(response_payload)


def update_supabase_password(*, subject: Optional[str], email: str, password: str) -> SupabaseIdentity:
    settings = get_settings()
    if not (settings.auth_mode.lower() == "supabase" and settings.supabase_url and settings.supabase_service_role_key):
        raise RuntimeError("Supabase admin provisioning is not enabled")

    target_subject = str(subject or "").strip()
    if not target_subject:
        existing = _find_supabase_user_by_email(email)
        if existing is None:
            raise ValueError("User is not provisioned in Supabase Auth")
        target_subject = str(existing.get("id") or "").strip()
        if not target_subject:
            raise ValueError("Invalid Supabase user lookup response")

    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{target_subject}",
        data=json.dumps({"password": password}).encode("utf-8"),
        headers=_supabase_admin_headers(),
        method="PUT",
    )

    try:
        response_payload = _request_json(request)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(detail or "Unable to update Supabase auth user password") from exc
    except URLError as exc:
        raise RuntimeError("Unable to reach Supabase Auth admin API") from exc

    if not response_payload.get("id") or not response_payload.get("email"):
        raise ValueError("Invalid Supabase admin response while updating password")
    return _identity_from_payload(response_payload)
