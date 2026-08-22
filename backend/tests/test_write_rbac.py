from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from app.models import Robot, RobotModel, Site

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)


def _robot(db_session) -> Robot:
    site = Site(id=uuid.uuid4(), site_code=f"SITE-{uuid.uuid4().hex[:8]}", name="RBAC Site", timezone="UTC")
    model = RobotModel(
        id=uuid.uuid4(),
        model_code=f"MODEL-{uuid.uuid4().hex[:8]}",
        manufacturer="Acme",
        name="RBAC Model",
        category="inspection",
    )
    robot = Robot(
        id=uuid.uuid4(),
        robot_code=f"ROBOT-{uuid.uuid4().hex[:8]}",
        name="RBAC Robot",
        serial_number=f"SERIAL-{uuid.uuid4().hex[:8]}",
        model_id=model.id,
        site_id=site.id,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add_all([site, model, robot])
    db_session.commit()
    db_session.refresh(robot)
    return robot


def _site_payload():
    return {"site_code": f"SITE-{uuid.uuid4().hex[:8]}", "name": "New Site", "timezone": "UTC"}


def _model_payload():
    return {
        "model_code": f"MODEL-{uuid.uuid4().hex[:8]}",
        "manufacturer": "Acme",
        "name": "New Model",
        "category": "inspection",
    }


def _robot_payload():
    return {
        "robot_code": f"ROBOT-{uuid.uuid4().hex[:8]}",
        "name": "New Robot",
        "serial_number": f"SERIAL-{uuid.uuid4().hex[:8]}",
        "model_id": str(uuid.uuid4()),
        "site_id": str(uuid.uuid4()),
        "status": "active",
        "installed_at": "2025-01-01T00:00:00Z",
    }


def test_unauthenticated_writes_are_401(unauthenticated_client):
    assert unauthenticated_client.post("/api/v1/robots", json=_robot_payload()).status_code == 401
    assert unauthenticated_client.post("/api/v1/sites", json=_site_payload()).status_code == 401
    assert unauthenticated_client.post("/api/v1/robot-models", json=_model_payload()).status_code == 401
    assert unauthenticated_client.patch(f"/api/v1/robots/{uuid.uuid4()}/status", json={"status": "idle"}).status_code == 401


def test_invalid_authentication_is_401(unauthenticated_client):
    unauthenticated_client.headers.update({"Authorization": "Bearer invalid-token"})
    assert unauthenticated_client.delete(f"/api/v1/robots/{uuid.uuid4()}").status_code == 401


def test_viewer_cannot_write_or_use_operational_status(viewer_client, db_session):
    robot = _robot(db_session)
    assert viewer_client.post("/api/v1/robots", json=_robot_payload()).status_code == 403
    assert viewer_client.patch(f"/api/v1/robots/{robot.id}", json={"name": "Nope"}).status_code == 403
    assert viewer_client.delete(f"/api/v1/robots/{robot.id}").status_code == 403
    assert viewer_client.post("/api/v1/sites", json=_site_payload()).status_code == 403
    assert viewer_client.patch(f"/api/v1/sites/{uuid.uuid4()}", json={"name": "Nope"}).status_code == 403
    assert viewer_client.delete(f"/api/v1/sites/{uuid.uuid4()}").status_code == 403
    assert viewer_client.post("/api/v1/robot-models", json=_model_payload()).status_code == 403
    assert viewer_client.patch(f"/api/v1/robot-models/{uuid.uuid4()}", json={"name": "Nope"}).status_code == 403
    assert viewer_client.delete(f"/api/v1/robot-models/{uuid.uuid4()}").status_code == 403
    assert viewer_client.patch(f"/api/v1/robots/{robot.id}/status", json={"status": "idle"}).status_code == 403


def test_reads_remain_unauthenticated(unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/robots").status_code == 200
    assert unauthenticated_client.get("/api/v1/dashboard/robot-status").status_code == 200


def test_viewer_can_read(viewer_client):
    assert viewer_client.get("/api/v1/robots").status_code == 200
    assert viewer_client.get("/api/v1/dashboard/robot-status").status_code == 200


@pytest.mark.parametrize("role", ["viewer", "operator", "admin"])
def test_authenticated_roles_can_read_current_user(role_client, role):
    from app.models import UserRole

    response = role_client(UserRole(role)).get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == role


@pytest.mark.parametrize("robot_status", ["active", "idle", "maintenance", "offline"])
def test_operator_can_update_operational_status(operator_client, db_session, robot_status):
    robot = _robot(db_session)
    response = operator_client.patch(f"/api/v1/robots/{robot.id}/status", json={"status": robot_status})
    assert response.status_code == 200
    assert response.json()["status"] == robot_status
    assert response.json()["robot_code"] == robot.robot_code


def test_operator_cannot_use_structural_robot_writes(operator_client, db_session):
    robot = _robot(db_session)
    assert operator_client.patch(f"/api/v1/robots/{robot.id}", json={"name": "Nope"}).status_code == 403
    assert operator_client.post("/api/v1/robots", json=_robot_payload()).status_code == 403
    assert operator_client.delete(f"/api/v1/robots/{robot.id}").status_code == 403
    assert operator_client.post("/api/v1/sites", json=_site_payload()).status_code == 403
    assert operator_client.patch(f"/api/v1/sites/{uuid.uuid4()}", json={"name": "Nope"}).status_code == 403
    assert operator_client.delete(f"/api/v1/sites/{uuid.uuid4()}").status_code == 403
    assert operator_client.post("/api/v1/robot-models", json=_model_payload()).status_code == 403
    assert operator_client.patch(f"/api/v1/robot-models/{uuid.uuid4()}", json={"name": "Nope"}).status_code == 403
    assert operator_client.delete(f"/api/v1/robot-models/{uuid.uuid4()}").status_code == 403


def test_operator_cannot_decommission_robot(operator_client, db_session):
    robot = _robot(db_session)
    response = operator_client.patch(f"/api/v1/robots/{robot.id}/status", json={"status": "decommissioned"})
    assert response.status_code == 422
    assert db_session.get(Robot, robot.id).status.value == "active"


def test_admin_can_use_operational_status(admin_client, db_session):
    robot = _robot(db_session)
    response = admin_client.patch(f"/api/v1/robots/{robot.id}/status", json={"status": "maintenance"})
    assert response.status_code == 200
    assert response.json()["status"] == "maintenance"
