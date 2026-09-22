from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.security import hash_password, issue_access_token, verify_password
from app.main import app
from app.models import AuthSession, User, UserRole


@pytest.fixture()
def auth_client(unauthenticated_client):
    return unauthenticated_client


def _create_user(db_session, *, email: str, password: str = "Passw0rd!", is_active: bool = True, role: UserRole = UserRole.VIEWER):
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_settings_require_explicit_jwt_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-value-for-local-tests-123")
    settings = Settings(_env_file=None)
    assert settings.jwt_secret_key == "test-jwt-secret-value-for-local-tests-123"


def test_password_hashing_and_verification(db_session):
    plain = "Passw0rd!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_login_success_returns_token(auth_client, db_session):
    user = _create_user(db_session, email="viewer@example.com")

    response = auth_client.post("/api/v1/auth/login", data={"username": user.email, "password": "Passw0rd!"})

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "password_hash" not in body
    assert response.headers["x-ratelimit-limit"] == "10"
    assert response.headers["x-ratelimit-remaining"] == "9"
    session = db_session.query(AuthSession).filter_by(user_id=user.id).one()
    assert session.revoked_at is None


def test_login_rejects_invalid_credentials(auth_client, db_session):
    _create_user(db_session, email="viewer@example.com")

    response = auth_client.post("/api/v1/auth/login", data={"username": "viewer@example.com", "password": "WrongPass!"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."

    response = auth_client.post("/api/v1/auth/login", data={"username": "unknown@example.com", "password": "Passw0rd!"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_login_rate_limit_returns_retry_headers(auth_client, db_session, monkeypatch):
    _create_user(db_session, email="rate-limit@example.com")
    monkeypatch.setattr(get_settings(), "login_rate_limit", 2)

    responses = [
        auth_client.post(
            "/api/v1/auth/login",
            data={"username": "rate-limit@example.com", "password": "WrongPass!"},
        )
        for _ in range(3)
    ]

    assert [response.status_code for response in responses[:2]] == [401] * 2
    rejected = responses[-1]
    assert rejected.status_code == 429
    assert rejected.json()["detail"] == "Rate limit exceeded. Retry later."
    assert rejected.headers["x-ratelimit-limit"] == "2"
    assert rejected.headers["x-ratelimit-remaining"] == "0"
    assert int(rejected.headers["retry-after"]) >= 1


def test_login_rejects_inactive_user(auth_client, db_session):
    user = _create_user(db_session, email="inactive@example.com", is_active=False)

    response = auth_client.post("/api/v1/auth/login", data={"username": user.email, "password": "Passw0rd!"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user."


def test_me_returns_safe_fields(auth_client, db_session):
    user = _create_user(db_session, email="me@example.com", role=UserRole.ADMIN)
    token = issue_access_token(db_session, user.id)

    response = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert body["role"] == "admin"
    assert body["is_active"] is True
    assert "password_hash" not in body


def test_token_validation_rejects_bad_requests(auth_client, db_session):
    user = _create_user(db_session, email="token@example.com")

    valid = issue_access_token(db_session, user.id)
    response = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {valid}"})
    assert response.status_code == 200

    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 401

    response = auth_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed.token.value"})
    assert response.status_code == 401

    response = auth_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_token_validation_rejects_inactive_and_missing_user(auth_client, db_session):
    user = _create_user(db_session, email="inactive-token@example.com", is_active=False)
    inactive_token = issue_access_token(db_session, user.id)
    response = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {inactive_token}"})
    assert response.status_code == 401

    missing_user = _create_user(db_session, email="deleted-token@example.com")
    missing_token = issue_access_token(db_session, missing_user.id)
    db_session.delete(missing_user)
    db_session.commit()
    response = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {missing_token}"})
    assert response.status_code == 401


def test_logout_revokes_only_the_presented_session(auth_client, db_session):
    user = _create_user(db_session, email="logout@example.com")
    first_token = issue_access_token(db_session, user.id)
    second_token = issue_access_token(db_session, user.id)

    response = auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {first_token}"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {first_token}"},
    ).status_code == 401
    assert auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second_token}"},
    ).status_code == 200


def test_logout_requires_an_active_session(auth_client):
    assert auth_client.post("/api/v1/auth/logout").status_code == 401
