from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.auth import ApiKey, AuthChallenge, PasswordResetToken, User, UserSession, WorkspaceSetting
from backend.models.onboarding import OnboardingProgress
from backend.models.portfolio import Workspace
from backend.services.auth.password import hash_password, verify_password
from backend.services.auth.session import sha256_hex
from backend.services.rate_limit import reset_rate_limiter


@pytest.fixture(autouse=True)
def default_local_auth(monkeypatch, request) -> None:
    if "supabase" in request.node.name:
        return
    monkeypatch.setattr("backend.routers.auth.is_supabase_auth_enabled", lambda: False)


@pytest.fixture(autouse=True)
def clear_rate_limiter_state() -> None:
    reset_rate_limiter()


def seed_user(db: Session, *, email: str = "owner@example.com", password: str = "secret123", totp: bool = False) -> User:
    workspace = Workspace(
        name=f"Workspace {email}",
        slug=email.replace("@", "-").replace(".", "-"),
        reporting_currency="USD",
        timezone="UTC",
        plan="starter",
    )
    db.add(workspace)
    db.flush()
    user = User(
        workspace_id=workspace.id,
        email=email,
        display_name="Owner",
        password_hash=hash_password(password),
        role="owner",
        scope="All clients",
        totp_enabled=totp,
        totp_secret="test-secret" if totp else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_login_sets_session_and_csrf_cookies(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session)

    response = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})

    assert response.status_code == 200
    body = response.json()
    assert body["requires_totp"] is False
    assert body["user"]["email"] == user.email
    assert "__crb_session" in response.cookies
    assert "__crb_csrf" in response.cookies


def test_register_creates_workspace_settings_and_onboarding_state(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "workspace_name": "Aldridge Family Office",
            "display_name": "Helena Voss",
            "email": "helena@example.com",
            "password": "secret123",
            "timezone": "Europe/Zurich",
            "reporting_currency": "CHF",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "helena@example.com"
    assert body["user"]["workspace_name"] == "Aldridge Family Office"
    assert "__crb_session" in response.cookies

    user = db_session.scalar(select(User).where(User.email == "helena@example.com"))
    assert user is not None
    workspace = db_session.get(Workspace, user.workspace_id)
    assert workspace is not None
    assert workspace.slug == "aldridge-family-office"
    assert workspace.reporting_currency == "CHF"
    assert workspace.timezone == "Europe/Zurich"

    settings = db_session.get(WorkspaceSetting, user.workspace_id)
    assert settings is not None
    assert settings.reporting_currency == "CHF"

    onboarding = db_session.get(OnboardingProgress, user.workspace_id)
    assert onboarding is not None
    assert onboarding.current_step == 1
    assert onboarding.completed_steps_json == '["workspace_created"]'


def test_session_endpoint_uses_cookie_session(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session, email="session@example.com")
    login = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})
    assert login.status_code == 200

    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == user.email
    assert response.json()["user"]["workspace_name"] == f"Workspace {user.email}"


def test_logout_requires_matching_csrf(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session, email="logout@example.com")
    login = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})
    csrf = login.cookies.get("__crb_csrf")

    denied = client.post("/api/auth/logout")
    assert denied.status_code == 403

    ok = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert ok.status_code == 200


def test_totp_login_falls_back_to_password_only_when_totp_is_disabled(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session, email="totp@example.com", totp=True)

    login = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})

    assert login.status_code == 200
    body = login.json()
    assert body["requires_totp"] is False
    assert body["user"]["email"] == user.email
    assert login.cookies.get("__crb_session")

    verify = client.post(
        "/api/auth/totp/verify",
        json={"session_challenge": "disabled", "code": "000000"},
    )
    assert verify.status_code == 404


def test_forgot_password_invalidates_previous_tokens(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session, email="forgot@example.com")

    first = client.post("/api/auth/forgot-password", json={"email": user.email})
    second = client.post("/api/auth/forgot-password", json={"email": user.email})

    assert first.status_code == 200
    assert second.status_code == 200
    tokens = db_session.scalars(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    ).all()
    assert len(tokens) == 2
    invalidated = [token for token in tokens if token.invalidated_at is not None]
    assert len(invalidated) == 1


def test_reset_password_marks_token_used_and_revokes_sessions(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session, email="reset@example.com")
    login = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})
    assert login.status_code == 200
    csrf = login.cookies.get("__crb_csrf", "")

    client.post(
        "/api/auth/forgot-password",
        json={"email": user.email},
        headers={"X-CSRF-Token": csrf},
    )
    token_row = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.invalidated_at.is_(None),
        )
    )
    assert token_row is not None

    raw_reset_token = None
    # Reconstruct by creating a known token directly for the reset flow test.
    # This keeps the endpoint contract unchanged while still exercising the handler.
    raw_reset_token = "integration-reset-token"
    token_row.token_hash = __import__("hashlib").sha256(raw_reset_token.encode("utf-8")).hexdigest()
    db_session.commit()

    response = client.post(
        "/api/auth/reset-password",
        json={"token": raw_reset_token, "new_password": "new-secret456"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    db_session.refresh(user)
    db_session.refresh(token_row)
    assert token_row.used_at is not None
    assert verify_password("new-secret456", user.password_hash or "")
    sessions = db_session.scalars(
        select(UserSession).where(UserSession.user_id == user.id)
    ).all()
    assert sessions
    assert all(session.revoked_at is not None for session in sessions)


def test_api_key_can_authenticate_request(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session, email="apikey@example.com")
    raw_key = "crb_test_api_key"
    db_session.add(
        ApiKey(
            workspace_id=user.workspace_id,
            user_id=user.id,
            label="Integration",
            key_type="anthropic",
            key_prefix=raw_key[:10],
            lookup_hash=sha256_hex(raw_key),
            key_hash=hash_password(raw_key),
        )
    )
    db_session.commit()

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == user.email
    assert response.json()["user"]["workspace_name"] == f"Workspace {user.email}"


def test_api_key_updates_last_used_and_cannot_logout(client: TestClient, db_session: Session) -> None:
    user = seed_user(db_session, email="apikey-logout@example.com")
    raw_key = "crb_test_logout_key"
    api_key = ApiKey(
        workspace_id=user.workspace_id,
        user_id=user.id,
        label="Integration",
        key_type="anthropic",
        key_prefix=raw_key[:10],
        lookup_hash=sha256_hex(raw_key),
        key_hash=hash_password(raw_key),
    )
    db_session.add(api_key)
    db_session.commit()

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert me.status_code == 200

    db_session.refresh(api_key)
    assert api_key.last_used_at is not None

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {raw_key}"})
    assert logout.status_code == 400


def test_api_key_auth_resolves_the_key_owner_not_the_oldest_workspace_user(
    client: TestClient,
    db_session: Session,
) -> None:
    owner = seed_user(db_session, email="owner-key@example.com")
    analyst = User(
        workspace_id=owner.workspace_id,
        email="analyst-key@example.com",
        display_name="Analyst",
        password_hash=hash_password("secret123"),
        role="analyst",
        scope="EMEA book",
        totp_enabled=False,
    )
    db_session.add(analyst)
    db_session.flush()

    raw_key = "crb_test_owner_binding"
    db_session.add(
        ApiKey(
            workspace_id=owner.workspace_id,
            user_id=analyst.id,
            label="Analyst Integration",
            key_type="anthropic",
            key_prefix=raw_key[:10],
            lookup_hash=sha256_hex(raw_key),
            key_hash=hash_password(raw_key),
        )
    )
    db_session.commit()

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == analyst.email


def test_login_rate_limit_returns_429_with_retry_after(client: TestClient, db_session: Session, monkeypatch) -> None:
    user = seed_user(db_session, email="rate-limit-login@example.com", password="secret123")
    monkeypatch.setattr("backend.routers.auth.AUTH_RATE_LIMIT_MAX_REQUESTS", 2)

    first = client.post("/api/auth/login", json={"email": user.email, "password": "wrong"})
    second = client.post("/api/auth/login", json={"email": user.email, "password": "wrong"})
    third = client.post("/api/auth/login", json={"email": user.email, "password": "wrong"})

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert third.headers.get("Retry-After")


def test_register_rate_limit_returns_429_with_retry_after(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("backend.routers.auth.AUTH_RATE_LIMIT_MAX_REQUESTS", 2)
    payload = {
        "workspace_name": "Rate Limit Office",
        "display_name": "Rate Limit Owner",
        "email": "rate-limit-register@example.com",
        "password": "secret123",
        "timezone": "UTC",
        "reporting_currency": "USD",
    }

    first = client.post("/api/auth/register", json=payload)
    second = client.post("/api/auth/register", json=payload)
    third = client.post("/api/auth/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert third.status_code == 429
    assert third.headers.get("Retry-After")


def test_forgot_password_rate_limit_returns_429_with_retry_after(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    user = seed_user(db_session, email="rate-limit-forgot@example.com")
    monkeypatch.setattr("backend.routers.auth.AUTH_RATE_LIMIT_MAX_REQUESTS", 2)

    first = client.post("/api/auth/forgot-password", json={"email": user.email})
    second = client.post("/api/auth/forgot-password", json={"email": user.email})
    third = client.post("/api/auth/forgot-password", json={"email": user.email})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.headers.get("Retry-After")


def test_supabase_login_returns_access_token_for_provisioned_user(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    user = seed_user(db_session, email="supabase@example.com")

    monkeypatch.setattr("backend.routers.auth.is_supabase_auth_enabled", lambda: True)
    monkeypatch.setattr(
        "backend.routers.auth.authenticate_supabase_password",
        lambda **_: (
            "supabase-access-token",
            SimpleNamespace(
                subject="supabase-user-123",
                email=user.email,
                display_name="Supabase Owner",
            ),
        ),
    )

    response = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "supabase-access-token"
    assert body["user"]["email"] == user.email
    assert "__crb_session" not in response.cookies

    db_session.refresh(user)
    assert user.auth_provider == "supabase"
    assert user.auth_subject == "supabase-user-123"


def test_supabase_register_provisions_auth_identity_and_returns_access_token(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr("backend.routers.auth.is_supabase_auth_enabled", lambda: True)
    monkeypatch.setattr(
        "backend.routers.auth.create_supabase_password_user",
        lambda **_: SimpleNamespace(
            subject="supabase-register-789",
            email="new-supabase@example.com",
            display_name="New Supabase User",
        ),
    )
    monkeypatch.setattr(
        "backend.routers.auth.authenticate_supabase_password",
        lambda **_: (
            "supabase-register-token",
            SimpleNamespace(
                subject="supabase-register-789",
                email="new-supabase@example.com",
                display_name="New Supabase User",
            ),
        ),
    )

    response = client.post(
        "/api/auth/register",
        json={
            "workspace_name": "Supabase Workspace",
            "display_name": "New Supabase User",
            "email": "new-supabase@example.com",
            "password": "secret123",
            "timezone": "UTC",
            "reporting_currency": "USD",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "supabase-register-token"
    assert body["user"]["email"] == "new-supabase@example.com"
    assert "__crb_session" not in response.cookies

    user = db_session.scalar(select(User).where(User.email == "new-supabase@example.com"))
    assert user is not None
    assert user.auth_provider == "supabase"
    assert user.auth_subject == "supabase-register-789"


def test_supabase_bearer_token_can_resolve_session(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    user = seed_user(db_session, email="supabase-session@example.com")
    user.auth_provider = "supabase"
    user.auth_subject = "supabase-subject-456"
    db_session.commit()

    monkeypatch.setattr(
        "backend.routers.auth.resolve_supabase_identity",
        lambda token: (
            SimpleNamespace(
                subject="supabase-subject-456",
                email=user.email,
                display_name=user.display_name,
            )
            if token == "supabase-session-token"
            else None
        ),
    )

    response = client.get(
        "/api/auth/session",
        headers={"Authorization": "Bearer supabase-session-token"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == user.email
    assert response.json()["user"]["workspace_name"] == f"Workspace {user.email}"


def test_supabase_reset_password_updates_upstream_identity_and_consumes_token(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    user = seed_user(db_session, email="supabase-reset@example.com")
    user.auth_provider = "supabase"
    user.auth_subject = "supabase-subject-reset-123"
    db_session.commit()

    client.post("/api/auth/forgot-password", json={"email": user.email})
    token_row = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.invalidated_at.is_(None),
        )
    )
    assert token_row is not None
    raw_reset_token = "supabase-reset-token"
    token_row.token_hash = hashlib.sha256(raw_reset_token.encode("utf-8")).hexdigest()
    db_session.commit()

    calls: dict[str, str] = {}
    monkeypatch.setattr("backend.routers.auth.is_supabase_auth_enabled", lambda: True)

    def fake_update_supabase_password(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(
            subject="supabase-subject-reset-123",
            email=user.email,
            display_name=user.display_name,
        )

    monkeypatch.setattr("backend.routers.auth.update_supabase_password", fake_update_supabase_password)

    response = client.post(
        "/api/auth/reset-password",
        json={"token": raw_reset_token, "new_password": "new-secret456"},
        headers={"Authorization": "Bearer reset-flow-token"},
    )

    assert response.status_code == 200
    assert calls["subject"] == "supabase-subject-reset-123"
    assert calls["email"] == user.email
    assert calls["password"] == "new-secret456"
    db_session.refresh(token_row)
    assert token_row.used_at is not None


def test_supabase_reset_password_does_not_consume_token_when_upstream_update_fails(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    user = seed_user(db_session, email="supabase-reset-fail@example.com")
    user.auth_provider = "supabase"
    user.auth_subject = "supabase-subject-reset-fail-123"
    db_session.commit()

    client.post("/api/auth/forgot-password", json={"email": user.email})
    token_row = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.invalidated_at.is_(None),
        )
    )
    assert token_row is not None
    raw_reset_token = "supabase-reset-fail-token"
    token_row.token_hash = hashlib.sha256(raw_reset_token.encode("utf-8")).hexdigest()
    db_session.commit()

    monkeypatch.setattr("backend.routers.auth.is_supabase_auth_enabled", lambda: True)
    monkeypatch.setattr(
        "backend.routers.auth.update_supabase_password",
        lambda **_: (_ for _ in ()).throw(RuntimeError("Unable to reach Supabase Auth admin API")),
    )

    response = client.post(
        "/api/auth/reset-password",
        json={"token": raw_reset_token, "new_password": "new-secret456"},
        headers={"Authorization": "Bearer reset-flow-token"},
    )

    assert response.status_code == 503
    db_session.refresh(token_row)
    assert token_row.used_at is None
