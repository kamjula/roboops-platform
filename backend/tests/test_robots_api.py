"""API tests for the robots CRUD endpoints."""
from __future__ import annotations

import uuid

import pytest


def _robot_payload(site_id, model_id, code, serial):
    return {
        "robot_code": code,
        "name": "Test Robot",
        "serial_number": serial,
        "model_id": model_id,
        "site_id": site_id,
        "status": "active",
        "installed_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture()
def site_and_model(client):
    site = client.post(
        "/api/v1/sites",
        json={"site_code": "STE-R1", "name": "Robot Site", "timezone": "UTC"},
    ).json()
    model = client.post(
        "/api/v1/robot-models",
        json={"model_code": "MDL-R1", "manufacturer": "Acme", "name": "Scout", "category": "inspection"},
    ).json()
    return site, model


def test_create_robot(client, site_and_model):
    site, model = site_and_model
    payload = _robot_payload(site["id"], model["id"], "RBT-100", "SN-100")
    resp = client.post("/api/v1/robots", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["robot_code"] == "RBT-100"
    assert "id" in body


def test_create_robot_invalid_site(client, site_and_model):
    _, model = site_and_model
    payload = _robot_payload(str(uuid.uuid4()), model["id"], "RBT-101", "SN-101")
    resp = client.post("/api/v1/robots", json=payload)
    assert resp.status_code == 422


def test_create_robot_invalid_model(client, site_and_model):
    site, _ = site_and_model
    payload = _robot_payload(site["id"], str(uuid.uuid4()), "RBT-102", "SN-102")
    resp = client.post("/api/v1/robots", json=payload)
    assert resp.status_code == 422 


def test_create_robot_duplicate_code_conflict(client, site_and_model):
    site, model = site_and_model
    client.post("/api/v1/robots", json=_robot_payload(site["id"], model["id"], "RBT-200", "SN-200"))
    payload = _robot_payload(site["id"], model["id"], "RBT-200", "SN-201")
    resp = client.post("/api/v1/robots", json=payload)
    assert resp.status_code == 409


def test_create_robot_duplicate_serial_conflict(client, site_and_model):
    site, model = site_and_model
    client.post("/api/v1/robots", json=_robot_payload(site["id"], model["id"], "RBT-210", "SN-210"))
    payload = _robot_payload(site["id"], model["id"], "RBT-211", "SN-210")
    resp = client.post("/api/v1/robots", json=payload)
    assert resp.status_code == 409


def test_list_robots_pagination_and_order(client, site_and_model):
    site, model = site_and_model
    for i in range(5):
        payload = _robot_payload(site["id"], model["id"], f"RBT-P{i}", f"SN-P{i}")
        client.post("/api/v1/robots", json=payload)
    resp = client.get("/api/v1/robots", params={"skip": 0, "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    resp_all = client.get("/api/v1/robots", params={"skip": 0, "limit": 100})
    codes = [r["robot_code"] for r in resp_all.json()]
    assert codes == sorted(codes)


def test_get_robot(client, site_and_model):
    site, model = site_and_model
    payload = _robot_payload(site["id"], model["id"], "RBT-300", "SN-300")
    created = client.post("/api/v1/robots", json=payload).json()
    resp = client.get(f"/api/v1/robots/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_robot_not_found(client):
    resp = client.get(f"/api/v1/robots/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_robot_invalid_uuid(client):
    resp = client.get("/api/v1/robots/not-a-uuid")
    assert resp.status_code == 422


def test_update_robot_partial(client, site_and_model):
    site, model = site_and_model
    payload = _robot_payload(site["id"], model["id"], "RBT-400", "SN-400")
    created = client.post("/api/v1/robots", json=payload).json()
    resp = client.patch(f"/api/v1/robots/{created['id']}", json={"name": "Renamed Robot"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed Robot"
    assert body["robot_code"] == "RBT-400"


def test_update_robot_not_found(client):
    resp = client.patch(f"/api/v1/robots/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


def test_update_robot_invalid_site(client, site_and_model):
    site, model = site_and_model
    payload = _robot_payload(site["id"], model["id"], "RBT-410", "SN-410")
    created = client.post("/api/v1/robots", json=payload).json()
    resp = client.patch(f"/api/v1/robots/{created['id']}", json={"site_id": str(uuid.uuid4())})
    assert resp.status_code == 422


def test_update_robot_invalid_model(client, site_and_model):
    site, model = site_and_model
    payload = _robot_payload(site["id"], model["id"], "RBT-420", "SN-420")
    created = client.post("/api/v1/robots", json=payload).json()
    resp = client.patch(f"/api/v1/robots/{created['id']}", json={"model_id": str(uuid.uuid4())})
    assert resp.status_code == 422


def test_update_robot_duplicate_conflict(client, site_and_model):
    site, model = site_and_model
    client.post("/api/v1/robots", json=_robot_payload(site["id"], model["id"], "RBT-430", "SN-430"))
    payload = _robot_payload(site["id"], model["id"], "RBT-431", "SN-431")
    second = client.post("/api/v1/robots", json=payload).json()
    resp = client.patch(f"/api/v1/robots/{second['id']}", json={"robot_code": "RBT-430"})
    assert resp.status_code == 409


def test_delete_robot(client, site_and_model):
    site, model = site_and_model
    payload = _robot_payload(site["id"], model["id"], "RBT-500", "SN-500")
    created = client.post("/api/v1/robots", json=payload).json()
    resp = client.delete(f"/api/v1/robots/{created['id']}")
    assert resp.status_code == 204
    resp2 = client.get(f"/api/v1/robots/{created['id']}")
    assert resp2.status_code == 404


def test_delete_robot_not_found(client):
    resp = client.delete(f"/api/v1/robots/{uuid.uuid4()}")
    assert resp.status_code == 404
