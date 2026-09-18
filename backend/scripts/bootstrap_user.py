"""Create the first local/deployment user without exposing a registration API."""
from __future__ import annotations

import argparse
import os

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import User, UserRole

MIN_PASSWORD_LENGTH = 12


def bootstrap_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: UserRole,
) -> tuple[User, bool]:
    """Create a user once; never overwrite an existing account's credentials."""
    try:
        normalized_email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    except ValidationError as exc:
        raise ValueError("A valid email address is required.") from exc
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must contain at least {MIN_PASSWORD_LENGTH} characters.")

    existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing is not None:
        return existing, False

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an initial RoboOps user idempotently.")
    parser.add_argument("--email", default=os.environ.get("ROBOOPS_BOOTSTRAP_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("ROBOOPS_BOOTSTRAP_PASSWORD"))
    parser.add_argument(
        "--role",
        choices=[role.value for role in UserRole],
        default=os.environ.get("ROBOOPS_BOOTSTRAP_ROLE", UserRole.ADMIN.value),
    )
    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error(
            "provide --email/--password or ROBOOPS_BOOTSTRAP_EMAIL/ROBOOPS_BOOTSTRAP_PASSWORD"
        )
    return args


def main() -> None:
    args = _arguments()
    db = SessionLocal()
    try:
        user, created = bootstrap_user(
            db,
            email=args.email,
            password=args.password,
            role=UserRole(args.role),
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    outcome = "created" if created else "already exists; credentials unchanged"
    print(f"Bootstrap user {user.email}: {outcome} ({user.role.value}).")


if __name__ == "__main__":
    main()
