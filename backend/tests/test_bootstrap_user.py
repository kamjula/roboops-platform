"""Initial-user bootstrap behavior against the isolated PostgreSQL test DB."""
from __future__ import annotations

import os
import uuid

import pytest

from app.core.security import verify_password
from app.models import UserRole
from scripts.bootstrap_user import bootstrap_user

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not set.",
)


def test_bootstrap_user_creates_once_without_rotating_existing_credentials(db_session):
    email = f"bootstrap-{uuid.uuid4()}@example.com"
    created_user, created = bootstrap_user(
        db_session,
        email=email.upper(),
        password="first-secure-password",
        role=UserRole.ADMIN,
    )
    assert created is True
    assert created_user.email == email
    assert created_user.role == UserRole.ADMIN
    assert verify_password("first-secure-password", created_user.password_hash)

    existing_user, created_again = bootstrap_user(
        db_session,
        email=email,
        password="different-secure-password",
        role=UserRole.VIEWER,
    )
    assert created_again is False
    assert existing_user.id == created_user.id
    assert existing_user.role == UserRole.ADMIN
    assert verify_password("first-secure-password", existing_user.password_hash)


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("not-an-email", "long-enough-password", "valid email"),
        ("valid@example.com", "short", "at least 12"),
    ],
)
def test_bootstrap_user_validates_credentials(db_session, email, password, message):
    with pytest.raises(ValueError, match=message):
        bootstrap_user(
            db_session,
            email=email,
            password=password,
            role=UserRole.ADMIN,
        )
