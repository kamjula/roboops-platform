"""Public demo issuance is opt-in and never grants write privileges."""
from __future__ import annotations

import os
import uuid

import pytest

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import User, UserRole

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set.")


def _user(db_session, role=UserRole.VIEWER, is_active=True):
    user = User(
        id=uuid.uuid4(), email="demo@roboops.example", password_hash=hash_password("not-for-public-use"),
        role=role, is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_demo_disabled_by_default(unauthenticated_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "roboops_public_demo_enabled", False)
    assert unauthenticated_client.post("/api/v1/auth/demo").status_code == 404


def test_demo_issues_only_viewer_session(unauthenticated_client, db_session, monkeypatch):
    _user(db_session)
    settings = get_settings()
    monkeypatch.setattr(settings, "roboops_public_demo_enabled", True)
    monkeypatch.setattr(settings, "roboops_public_demo_email", "demo@roboops.example")

    response = unauthenticated_client.post("/api/v1/auth/demo")
    assert response.status_code == 200
    assert response.headers["x-ratelimit-limit"] == "120"
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    identity = unauthenticated_client.get("/api/v1/auth/me", headers=headers)
    assert identity.status_code == 200
    assert identity.json()["role"] == "viewer"
    assert unauthenticated_client.get("/api/v1/dashboard/summary", headers=headers).status_code == 200
    assert unauthenticated_client.post("/api/v1/sites", json={"site_code": "X", "name": "X", "timezone": "UTC"}, headers=headers).status_code == 403


@pytest.mark.parametrize("role,active", [(UserRole.ADMIN, True), (UserRole.VIEWER, False)])
def test_demo_refuses_admin_or_inactive_user(unauthenticated_client, db_session, monkeypatch, role, active):
    _user(db_session, role=role, is_active=active)
    settings = get_settings()
    monkeypatch.setattr(settings, "roboops_public_demo_enabled", True)
    monkeypatch.setattr(settings, "roboops_public_demo_email", "demo@roboops.example")
    assert unauthenticated_client.post("/api/v1/auth/demo").status_code == 503
