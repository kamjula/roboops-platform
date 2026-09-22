from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.models import AuthSession, User, UserRole

settings = get_settings()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    session: AuthSession


def _encode_access_token(
    subject: str | uuid.UUID,
    session_id: uuid.UUID,
    *,
    issued_at: datetime,
    expires_at: datetime,
) -> str:
    if isinstance(subject, uuid.UUID):
        subject = str(subject)
    payload = {
        "sub": subject,
        "jti": str(session_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def issue_access_token(
    db: Session,
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Persist a server-side session and return its signed access token."""
    user_id = subject if isinstance(subject, uuid.UUID) else uuid.UUID(str(subject))
    now = datetime.now(timezone.utc)
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expiry_minutes))

    db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.expires_at <= now,
        )
    )
    auth_session = AuthSession(id=uuid.uuid4(), user_id=user_id, expires_at=expires_at)
    db.add(auth_session)
    db.commit()

    return _encode_access_token(
        user_id,
        auth_session.id,
        issued_at=now,
        expires_at=expires_at,
    )


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_authenticated_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedSession:
    if credentials is None:
        raise _credentials_exception()

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise _credentials_exception() from exc

    subject = payload.get("sub")
    jwt_id = payload.get("jti")
    if not subject or not jwt_id:
        raise _credentials_exception()

    try:
        user_id = uuid.UUID(str(subject))
        session_id = uuid.UUID(str(jwt_id))
    except ValueError as exc:
        raise _credentials_exception() from exc

    now = datetime.now(timezone.utc)
    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )
    if auth_session is None:
        raise _credentials_exception()

    user = db.get(User, user_id)
    if user is None:
        raise _credentials_exception()
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user.")

    return AuthenticatedSession(user=user, session=auth_session)


def get_current_user(auth: AuthenticatedSession = Depends(get_authenticated_session)) -> User:
    return auth.user


def require_roles(*allowed_roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return current_user

    return role_checker
