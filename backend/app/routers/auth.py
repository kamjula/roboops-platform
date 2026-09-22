from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import enforce_rate_limit
from app.core.security import create_access_token, get_current_user, verify_password
from app.database import get_db
from app.models import User
from app.schemas.user import UserMe

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserMe)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
