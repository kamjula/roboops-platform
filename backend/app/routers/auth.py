from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    AuthenticatedSession,
    get_authenticated_session,
    get_current_user,
    issue_access_token,
    verify_password,
)
from app.database import get_db
from app.models import User, UserRole
from app.schemas.user import UserMe

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/demo")
def login_public_demo(request: Request, response: Response, db: Session = Depends(get_db)):
    """Issue a short viewer session for an explicitly enabled synthetic-data demo."""
    settings = get_settings()
    if not settings.roboops_public_demo_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public demo is disabled.")

    # Bound session creation per client and across all clients on this instance.
    enforce_rate_limit(
        request, response, scope="public-demo-ip", subject=request.client.host if request.client else "unknown",
        limit=20, window_seconds=60,
    )
    enforce_rate_limit(
        request, response, scope="public-demo-global", subject="all", limit=120, window_seconds=60,
    )
    user = db.query(User).filter(User.email == settings.roboops_public_demo_email.lower()).one_or_none()
    if user is None or not user.is_active or user.role != UserRole.VIEWER:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Read-only demo is unavailable.")
    token = issue_access_token(db, user.id, expires_delta=timedelta(minutes=15))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    enforce_rate_limit(
        request,
        response,
        scope="auth-login",
        subject=form_data.username.strip().lower(),
        limit=settings.login_rate_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    user = db.query(User).filter(User.email == form_data.username).one_or_none()
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user.")

    token = issue_access_token(db, user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserMe)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    auth: AuthenticatedSession = Depends(get_authenticated_session),
    db: Session = Depends(get_db),
) -> Response:
    auth.session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
