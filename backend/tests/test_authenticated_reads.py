from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Robot, RobotModel, Site, UserRole

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)

COLLECTION_READ_ROUTES = [
    "/api/v1/sites",
    "/api/v1/robot-models",
    "/api/v1/robots",
    "/api/v1/dashboard/summary",
    "/api/v1/dashboard/robot-status",
    "/api/v1/dashboard/latest-alerts",
    "/api/v1/dashboard/health-summary",
    "/api/v1/dashboard/site-summary",
    "/api/v1/dashboard/maintenance-summary",
]


@pytest.fixture()
def detail_routes(db_session):
    site = Site(
        site_code=f"SITE-{uuid.uuid4().hex[:8]}",
        name="Read Test Site",
        timezone="UTC",
    )
    robot_model = RobotModel(
        model_code=f"MODEL-{uuid.uuid4().hex[:8]}",
        manufacturer="Acme",
        name="Read Test Model",
        category="inspection",
    )
    db_session.add_all([site, robot_model])
    db_session.commit()

    robot = Robot(
        robot_code=f"ROBOT-{uuid.uuid4().hex[:8]}",
        name="Read Test Robot",
        serial_number=f"SERIAL-{uuid.uuid4().hex[:8]}",
        model_id=robot_model.id,
        site_id=site.id,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    return [
        f"/api/v1/sites/{site.id}",
        f"/api/v1/robot-models/{robot_model.id}",
        f"/api/v1/robots/{robot.id}",
    ]


@pytest.mark.parametrize("path", COLLECTION_READ_ROUTES)
def test_unauthenticated_collection_reads_require_authentication(unauthenticated_client, path):
    assert unauthenticated_client.get(path).status_code == 401


def test_invalid_and_expired_tokens_require_authentication(unauthenticated_client, db_session):
    from app.core.security import create_access_token, hash_password
    from app.models import User

    user = User(
        email=f"token-{uuid.uuid4()}@example.com",
        password_hash=hash_password("Passw0rd!"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    db_session.commit()

    expired_token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))
    for token in ("malformed-token", expired_token):
        response = unauthenticated_client.get(
            "/api/v1/robots",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


@pytest.mark.parametrize("role", [UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])
@pytest.mark.parametrize("path", COLLECTION_READ_ROUTES)
def test_all_roles_can_read_collection_endpoints(role_client, role, path):
    assert role_client(role).get(path).status_code == 200


def test_unauthenticated_detail_reads_require_authentication(unauthenticated_client, detail_routes):
    for path in detail_routes:
        assert unauthenticated_client.get(path).status_code == 401


@pytest.mark.parametrize("role", [UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])
def test_all_roles_can_read_detail_endpoints(role_client, role, detail_routes):
    client = role_client(role)
    for path in detail_routes:
        assert client.get(path).status_code == 200


def test_health_remains_public(unauthenticated_client):
    response = unauthenticated_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_remains_public(unauthenticated_client, db_session):
    from app.core.security import hash_password
    from app.models import User

    user = User(
        email=f"login-{uuid.uuid4()}@example.com",
        password_hash=hash_password("Passw0rd!"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    db_session.commit()

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "Passw0rd!"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_auth_me_requires_authentication(unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/auth/me").status_code == 401
