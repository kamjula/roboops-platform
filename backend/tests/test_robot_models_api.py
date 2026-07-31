"""API tests for the robot-models CRUD endpoints."""
from __future__ import annotations

import os
import uuid
import pytest

from datetime import datetime, timezone

from app.models.robot import Robot, RobotStatus
from app.models.robot_model import RobotModel
from app.models.site import Site

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)

def _model_payload(code):
    return {"model_code": code, "manufacturer": "Acme", "name": "Scout", "category": "inspection"}


def test_create_robot_model(client):
    resp = client.post("/api/v1/robot-models", json=_model_payload("MDL-100"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["model_code"] == "MDL-100"
    assert "id" in body


def test_create_robot_model_duplicate_conflict(client):
    client.post("/api/v1/robot-models", json=_model_payload("MDL-101"))
    resp = client.post("/api/v1/robot-models", json=_model_payload("MDL-101"))
    assert resp.status_code == 409


def test_list_robot_models_pagination_and_order(client):
    for i in range(5):
        client.post("/api/v1/robot-models", json=_model_payload(f"MDL-P{i}"))
    resp = client.get("/api/v1/robot-models", params={"skip": 0, "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    resp_all = client.get("/api/v1/robot-models", params={"skip": 0, "limit": 100})
    codes = [m["model_code"] for m in resp_all.json()]
    assert codes == sorted(codes)


def test_get_robot_model(client):
    created = client.post("/api/v1/robot-models", json=_model_payload("MDL-200")).json()
    resp = client.get(f"/api/v1/robot-models/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_robot_model_not_found(client):
    resp = client.get(f"/api/v1/robot-models/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_robot_model_invalid_uuid(client):
    resp = client.get("/api/v1/robot-models/not-a-uuid")
    assert resp.status_code == 422


def test_update_robot_model_partial(client):
    created = client.post("/api/v1/robot-models", json=_model_payload("MDL-300")).json()
    resp = client.patch(f"/api/v1/robot-models/{created['id']}", json={"name": "Updated"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated"
    assert body["model_code"] == "MDL-300"


def test_update_robot_model_not_found(client):
    resp = client.patch(f"/api/v1/robot-models/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


def test_update_robot_model_duplicate_conflict(client):
    client.post("/api/v1/robot-models", json=_model_payload("MDL-400"))
    second = client.post("/api/v1/robot-models", json=_model_payload("MDL-401")).json()
    resp = client.patch(f"/api/v1/robot-models/{second['id']}", json={"model_code": "MDL-400"})
    assert resp.status_code == 409


def test_delete_robot_model(client):
    created = client.post("/api/v1/robot-models", json=_model_payload("MDL-500")).json()
    resp = client.delete(f"/api/v1/robot-models/{created['id']}")
    assert resp.status_code == 204
    resp2 = client.get(f"/api/v1/robot-models/{created['id']}")
    assert resp2.status_code == 404


def test_delete_robot_model_not_found(client):
    resp = client.delete(f"/api/v1/robot-models/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_delete_robot_model_conflict_when_referenced(client, db_session):
    site = Site(site_code="STE-700", name="Site 700", timezone="UTC")
    model = RobotModel(model_code="MDL-700", manufacturer="Acme", name="Scout", category="inspection")
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code="RBT-700",
        name="Robot 700",
        serial_number="SN-700",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()

    resp = client.delete(f"/api/v1/robot-models/{model.id}")
    assert resp.status_code == 409
