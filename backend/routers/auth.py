from __future__ import annotations

import json
import re
from datetime import timedelta
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.deps import get_db
from backend.models.auth import ApiKey, AuthChallenge, PasswordResetToken, User, UserSession, WorkspaceSetting
from backend.models.onboarding import OnboardingProgress
from backend.models.portfolio import Workspace
from backend.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    TotpVerifyRequest,
    UserResponse,
)
from backend.services.auth.password import hash_password, verify_password
from backend.services.auth.supabase import (
    authenticate_supabase_password,
    create_supabase_password_user,
    is_supabase_auth_enabled,
    resolve_supabase_identity,
    update_supabase_password,
)
from backend.services.rate_limit import allow_request
from backend.services.auth.session import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    ensure_utc,
    create_session,
    get_session_by_token,
    make_opaque_token,
    sha256_hex,
    utc_now,
)

router = APIRouter(prefix="/auth", tags=["auth"])
AuthContext = Tuple[Optional[UserSession], User]
AUTH_RATE_LIMIT_MAX_REQUESTS = 10
AUTH_RATE_LIMIT_WINDOW_SECONDS = 60


class ChangeEmailRequest(BaseModel):
    email: str


class ChangePasswordRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str


def _serialize_user(db: Session, user: User) -> UserResponse:
    workspace = db.get(Workspace, user.workspace_id)
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        workspace_id=user.workspace_id,
        workspace_name=workspace.name if workspace is not None else None,
    )


def _set_auth_cookies(response: Response, raw_session_token: str, csrf_secret: str) -> None:
    settings = get_settings()
    max_age = int(timedelta(days=settings.session_ttl_days).total_seconds())
    secure = settings.environment != "development"
    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_session_token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_secret,
        httponly=False,
        secure=secure,
        samesite="strict",
        max_age=max_age,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


def _slugify_workspace_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "workspace"


def _build_unique_workspace_slug(db: Session, workspace_name: str) -> str:
    base = _slugify_workspace_name(workspace_name)
    slug = base
    suffix = 2
    while db.scalar(select(Workspace.id).where(Workspace.slug == slug)) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def _bootstrap_workspace_membership(
    db: Session,
    *,
    workspace_name: str,
    display_name: str,
    email: str,
    password: Optional[str],
    timezone: str,
    reporting_currency: str,
    auth_provider: Optional[str] = None,
    auth_subject: Optional[str] = None,
) -> User:
    normalized_currency = str(reporting_currency or "CHF").strip().upper() or "CHF"
    normalized_timezone = str(timezone or "UTC").strip() or "UTC"
    workspace = Workspace(
        name=workspace_name.strip(),
        slug=_build_unique_workspace_slug(db, workspace_name),
        reporting_currency=normalized_currency,
        timezone=normalized_timezone,
        plan="starter",
    )
    db.add(workspace)
    db.flush()

    user = User(
        workspace_id=workspace.id,
        email=email.strip().lower(),
        display_name=display_name.strip(),
        password_hash=hash_password(password) if password else None,
        auth_provider=auth_provider,
        auth_subject=auth_subject,
        role="owner",
        scope="All clients",
        totp_enabled=False,
    )
    db.add(user)

    now = utc_now()
    db.add(
        WorkspaceSetting(
            workspace_id=workspace.id,
            reporting_currency=normalized_currency,
            updated_at=now,
        )
    )
    db.add(
        OnboardingProgress(
            workspace_id=workspace.id,
            current_step=1,
            completed_steps_json=json.dumps(["workspace_created"]),
            total_steps=5,
            last_step_completed_at=now,
        )
    )
    db.flush()
    return user


def _bearer_token(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value


def _resolve_api_key_user(db: Session, raw_token: str) -> Optional[User]:
    key = db.scalar(
        select(ApiKey).where(
            ApiKey.lookup_hash == sha256_hex(raw_token),
            ApiKey.revoked_at.is_(None),
        )
    )
    if key is None or not verify_password(raw_token, key.key_hash):
        return None

    user = db.scalar(
        select(User).where(
            User.id == key.user_id,
            User.workspace_id == key.workspace_id,
            User.disabled_at.is_(None),
        )
    )
    if user is None:
        return None

    key.last_used_at = utc_now()
    db.flush()
    return user


def _resolve_supabase_user(db: Session, raw_token: str) -> Optional[User]:
    try:
        identity = resolve_supabase_identity(raw_token)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if identity is None:
        return None

    user = db.scalar(select(User).where(User.auth_subject == identity.subject, User.disabled_at.is_(None)))
    if user is None:
        user = db.scalar(select(User).where(User.email == identity.email, User.disabled_at.is_(None)))
        if user is None:
            return None
        user.auth_provider = "supabase"
        user.auth_subject = identity.subject
        if not user.display_name:
            user.display_name = identity.display_name
        db.flush()
    return user


def _request_origin_identifier(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_auth_rate_limit(request: Request, route_name: str, email: Optional[str] = None) -> None:
    normalized_email = (email or "").strip().lower() or "anonymous"
    source = _request_origin_identifier(request)
    key = f"{route_name}:{source}:{normalized_email}"
    allowed, retry_after = allow_request(
        key,
        limit=AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    if allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many authentication attempts. Try again shortly.",
        headers={"Retry-After": str(retry_after)},
    )


def require_session(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthContext:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME) or _bearer_token(request)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session = get_session_by_token(db, raw_token)
    if session is not None:
        user = db.get(User, session.user_id)
        if user is None or user.disabled_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

        session.last_seen_at = utc_now()
        db.flush()
        return session, user

    user = _resolve_api_key_user(db, raw_token)
    if user is not None:
        return None, user

    user = _resolve_supabase_user(db, raw_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return None, user


def require_cookie_csrf(
    request: Request,
    x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if _bearer_token(request):
        return

    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_cookie:
        return

    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_cookie or not x_csrf_token or csrf_cookie != x_csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    _enforce_auth_rate_limit(request, "login", payload.email)
    if is_supabase_auth_enabled():
        try:
            access_token, identity = authenticate_supabase_password(email=payload.email, password=payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        user = db.scalar(select(User).where(User.auth_subject == identity.subject, User.disabled_at.is_(None)))
        if user is None:
            user = db.scalar(select(User).where(User.email == identity.email, User.disabled_at.is_(None)))
            if user is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not provisioned for this workspace")
            user.auth_provider = "supabase"
            user.auth_subject = identity.subject
            if not user.display_name:
                user.display_name = identity.display_name
            db.commit()

        return LoginResponse(user=_serialize_user(db, user), access_token=access_token)

    stmt = select(User).where(User.email == payload.email)
    user = db.scalar(stmt)
    if user is None or user.password_hash is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.disabled_at is not None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    session, raw_token = create_session(db, user, request.headers.get("user-agent", "unknown"))
    db.commit()
    _set_auth_cookies(response, raw_token, session.csrf_secret)
    return LoginResponse(user=_serialize_user(db, user))


@router.post("/register", response_model=LoginResponse)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    _enforce_auth_rate_limit(request, "register", payload.email)
    normalized_email = payload.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == normalized_email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists")

    if is_supabase_auth_enabled():
        try:
            identity = create_supabase_password_user(
                email=normalized_email,
                password=payload.password,
                display_name=payload.display_name.strip(),
            )
        except ValueError as exc:
            detail = str(exc)
            status_code = status.HTTP_409_CONFLICT if "already exists" in detail.lower() else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=status_code, detail=detail) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        user = _bootstrap_workspace_membership(
            db,
            workspace_name=payload.workspace_name,
            display_name=payload.display_name,
            email=normalized_email,
            password=None,
            timezone=payload.timezone,
            reporting_currency=payload.reporting_currency,
            auth_provider="supabase",
            auth_subject=identity.subject,
        )
        db.commit()

        try:
            access_token, _ = authenticate_supabase_password(
                email=normalized_email,
                password=payload.password,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Workspace created but unable to establish Supabase session") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        return LoginResponse(user=_serialize_user(db, user), access_token=access_token)

    user = _bootstrap_workspace_membership(
        db,
        workspace_name=payload.workspace_name,
        display_name=payload.display_name,
        email=normalized_email,
        password=payload.password,
        timezone=payload.timezone,
        reporting_currency=payload.reporting_currency,
        auth_provider="local",
    )
    session, raw_token = create_session(db, user, request.headers.get("user-agent", "unknown"))
    db.commit()
    _set_auth_cookies(response, raw_token, session.csrf_secret)
    return LoginResponse(user=_serialize_user(db, user))


@router.post("/totp/verify", response_model=LoginResponse)
def totp_verify(
    payload: TotpVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    # Roadmap: implement only with enrollment, recovery codes, and rate-limited challenge validation.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="TOTP verification is disabled",
    )


@router.get("/session", response_model=SessionResponse)
def get_session(
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_session),
    db: Session = Depends(get_db),
) -> SessionResponse:
    session, user = auth
    raw_token = request.cookies.get(SESSION_COOKIE_NAME) or _bearer_token(request)
    if raw_token and session is not None:
        _set_auth_cookies(response, raw_token, session.csrf_secret)
    return SessionResponse(user=_serialize_user(db, user))


@router.get("/me", response_model=SessionResponse)
def get_me(
    auth: AuthContext = Depends(require_session),
    db: Session = Depends(get_db),
) -> SessionResponse:
    _, user = auth
    return SessionResponse(user=_serialize_user(db, user))


@router.post("/logout", response_model=MessageResponse, dependencies=[Depends(require_cookie_csrf)])
def logout(
    response: Response,
    auth: AuthContext = Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    session, _ = auth
    if session is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key sessions cannot log out")
    session.revoked_at = utc_now()
    db.commit()
    _clear_auth_cookies(response)
    return MessageResponse(detail="Logged out")


@router.post("/logout-all", response_model=MessageResponse, dependencies=[Depends(require_cookie_csrf)])
def logout_all(
    response: Response,
    auth: AuthContext = Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    session, _ = auth
    if session is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key sessions cannot log out")
    db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == session.user_id,
            UserSession.session_family_id == session.session_family_id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=utc_now())
    )
    db.commit()
    _clear_auth_cookies(response)
    return MessageResponse(detail="All sessions revoked")


@router.put("/email", response_model=SessionResponse, dependencies=[Depends(require_cookie_csrf)])
def change_email(
    payload: ChangeEmailRequest,
    auth: AuthContext = Depends(require_session),
    db: Session = Depends(get_db),
) -> SessionResponse:
    _, user = auth
    normalized = payload.email.strip().lower()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")
    existing = db.scalar(select(User).where(User.email == normalized, User.id != user.id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists")
    user.email = normalized
    db.commit()
    db.refresh(user)
    return SessionResponse(user=_serialize_user(db, user))


@router.put("/password", response_model=MessageResponse, dependencies=[Depends(require_cookie_csrf)])
def change_password(
    payload: ChangePasswordRequest,
    auth: AuthContext = Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, user = auth
    if user.password_hash is not None and not verify_password(payload.current_password or "", user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    if is_supabase_auth_enabled():
        try:
            identity = update_supabase_password(
                subject=user.auth_subject,
                email=user.email,
                password=payload.new_password,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        user.auth_provider = "supabase"
        user.auth_subject = identity.subject
    else:
        user.password_hash = hash_password(payload.new_password)
    db.commit()
    return MessageResponse(detail="Password changed")


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    _enforce_auth_rate_limit(request, "forgot_password", payload.email)
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        return ForgotPasswordResponse(accepted=True)

    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.invalidated_at.is_(None),
        )
        .values(invalidated_at=utc_now())
    )
    reset_token = make_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=sha256_hex(reset_token),
            expires_at=utc_now() + timedelta(hours=1),
            requested_ip=None,
        )
    )
    db.commit()
    return ForgotPasswordResponse(accepted=True)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    token_hash = sha256_hex(payload.token)
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    reset_token = db.scalar(stmt)
    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.invalidated_at is not None
        or ensure_utc(reset_token.expires_at) <= utc_now()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")

    user = db.get(User, reset_token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")

    if is_supabase_auth_enabled():
        try:
            identity = update_supabase_password(
                subject=user.auth_subject,
                email=user.email,
                password=payload.new_password,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        user.auth_provider = "supabase"
        user.auth_subject = identity.subject
    else:
        user.password_hash = hash_password(payload.new_password)

    reset_token.used_at = utc_now()
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )
    db.execute(
        update(AuthChallenge)
        .where(AuthChallenge.user_id == user.id, AuthChallenge.consumed_at.is_(None))
        .values(consumed_at=utc_now())
    )
    db.commit()
    return MessageResponse(detail="Password reset")
