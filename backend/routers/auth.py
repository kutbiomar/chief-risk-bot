from __future__ import annotations

from datetime import timedelta
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.deps import get_db
from backend.models.auth import ApiKey, AuthChallenge, PasswordResetToken, User, UserSession
from backend.models.portfolio import Workspace
from backend.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
    SessionResponse,
    TotpVerifyRequest,
    UserResponse,
)
from backend.services.auth.password import hash_password, verify_password
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


@router.post("/totp/verify", response_model=LoginResponse)
def totp_verify(
    payload: TotpVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
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


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
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
