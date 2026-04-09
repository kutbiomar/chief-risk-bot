from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.auth import ApiKey, AuthChallenge, PasswordResetToken, User, UserSession
from backend.models.portfolio import Workspace
from backend.services.auth.password import hash_password, verify_password
from backend.services.auth.session import sha256_hex


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
