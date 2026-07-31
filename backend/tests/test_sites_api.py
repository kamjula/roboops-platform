"""API tests for the sites CRUD endpoints."""
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

def _site_payload(code):
    return {"site_code": code, "name": "Test Site", "address": "123 Main St", "timezone": "UTC"}


def test_create_site(client):
    resp = client.post("/api/v1/sites", json=_site_payload("STE-100"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["site_code"] == "STE-100"
    assert "id" in body


def test_create_site_duplicate_conflict(client):
    client.post("/api/v1/sites", json=_site_payload("STE-101"))
    resp = client.post("/api/v1/sites", json=_site_payload("STE-101"))
    assert resp.status_code == 409


def test_list_sites_pagination_and_order(client):
    for i in range(5):
        client.post("/api/v1/sites", json=_site_payload(f"STE-P{i}"))
    resp = client.get("/api/v1/sites", params={"skip": 0, "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    resp_all = client.get("/api/v1/sites", params={"skip": 0, "limit": 100})
    codes = [s["site_code"] for s in resp_all.json()]
    assert codes == sorted(codes)


def test_get_site(client):
    created = client.post("/api/v1/sites", json=_site_payload("STE-200")).json()
    resp = client.get(f"/api/v1/sites/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_site_not_found(client):
    resp = client.get(f"/api/v1/sites/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_site_invalid_uuid(client):
    resp = client.get("/api/v1/sites/not-a-uuid")
    assert resp.status_code == 422


def test_update_site_partial(client):
    created = client.post("/api/v1/sites", json=_site_payload("STE-300")).json()
    resp = client.patch(f"/api/v1/sites/{created['id']}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated Name"
    assert body["site_code"] == "STE-300"


def test_update_site_not_found(client):
    resp = client.patch(f"/api/v1/sites/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


def test_update_site_duplicate_conflict(client):
    client.post("/api/v1/sites", json=_site_payload("STE-400"))
    second = client.post("/api/v1/sites", json=_site_payload("STE-401")).json()
    resp = client.patch(f"/api/v1/sites/{second['id']}", json={"site_code": "STE-400"})
    assert resp.status_code == 409


def test_delete_site(client):
    created = client.post("/api/v1/sites", json=_site_payload("STE-500")).json()
    resp = client.delete(f"/api/v1/sites/{created['id']}")
    assert resp.status_code == 204
    resp2 = client.get(f"/api/v1/sites/{created['id']}")
    assert resp2.status_code == 404


def test_delete_site_not_found(client):
    resp = client.delete(f"/api/v1/sites/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_delete_site_conflict_when_referenced(client, db_session):
    site = Site(site_code="STE-600", name="Referenced Site", timezone="UTC")
    model = RobotModel(model_code="MDL-600", manufacturer="Acme", name="Scout", category="inspection")
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code="RBT-600",
        name="Robot 600",
        serial_number="SN-600",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()

    resp = client.delete(f"/api/v1/sites/{site.id}")
    assert resp.status_code == 409
