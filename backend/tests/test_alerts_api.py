"""API coverage for authenticated alert operations."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Alert, AlertSeverity, Robot, RobotModel, RobotStatus, Site

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set.")


def _seed_alerts(db_session):
    site = Site(site_code=f"STE-{uuid.uuid4().hex[:8]}", name="Alert Site", timezone="UTC")
    model = RobotModel(
        model_code=f"MDL-{uuid.uuid4().hex[:8]}", manufacturer="Acme", name="Scout", category="inspection"
    )
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code=f"RBT-{uuid.uuid4().hex[:8]}",
        name="Alert Robot",
        serial_number=f"SN-{uuid.uuid4().hex[:8]}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    now = datetime.now(timezone.utc)
    open_alert = Alert(
        robot_id=robot.id,
        severity=AlertSeverity.CRITICAL,
        alert_type="temperature_anomaly",
        message="Temperature condition exceeded the configured threshold.",
        triggered_at=now,
        created_at=now,
    )
    resolved_alert = Alert(
        robot_id=robot.id,
        severity=AlertSeverity.WARNING,
        alert_type="battery_low",
        message="Battery reading is below the configured threshold.",
        triggered_at=now - timedelta(hours=1),
        resolved_at=now - timedelta(minutes=30),
        created_at=now - timedelta(hours=1),
    )
    db_session.add_all([open_alert, resolved_alert])
    db_session.commit()
    return open_alert, resolved_alert


def test_alert_list_requires_authentication(unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/alerts").status_code == 401


def test_alert_list_defaults_to_open_and_enriches_robot(client, db_session):
    open_alert, _ = _seed_alerts(db_session)
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [str(open_alert.id)]
    assert payload[0]["robot_code"].startswith("RBT-")
    assert payload[0]["robot_name"] == "Alert Robot"
    assert payload[0]["resolved_at"] is None


def test_alert_list_filters_state_and_severity(client, db_session):
    open_alert, resolved_alert = _seed_alerts(db_session)
    resolved = client.get("/api/v1/alerts", params={"status": "resolved"}).json()
    assert [item["id"] for item in resolved] == [str(resolved_alert.id)]
    critical = client.get("/api/v1/alerts", params={"status": "all", "severity": "critical"}).json()
    assert [item["id"] for item in critical] == [str(open_alert.id)]


def test_alert_list_validates_filters(client):
    assert client.get("/api/v1/alerts", params={"status": "invalid"}).status_code == 422
    assert client.get("/api/v1/alerts", params={"severity": "emergency"}).status_code == 422
    assert client.get("/api/v1/alerts", params={"limit": 0}).status_code == 422


def test_viewer_cannot_resolve_alert(viewer_client, db_session):
    open_alert, _ = _seed_alerts(db_session)
    assert viewer_client.patch(f"/api/v1/alerts/{open_alert.id}/resolve").status_code == 403


@pytest.mark.parametrize("client_fixture", ["operator_client", "admin_client"])
def test_operator_and_admin_resolve_alert_idempotently(request, client_fixture, db_session):
    role_client = request.getfixturevalue(client_fixture)
    open_alert, _ = _seed_alerts(db_session)
    first = role_client.patch(f"/api/v1/alerts/{open_alert.id}/resolve")
    assert first.status_code == 200
    first_resolved_at = first.json()["resolved_at"]
    assert first_resolved_at is not None
    second = role_client.patch(f"/api/v1/alerts/{open_alert.id}/resolve")
    assert second.status_code == 200
    assert second.json()["resolved_at"] == first_resolved_at


def test_resolve_missing_alert_returns_404(operator_client):
    response = operator_client.patch(f"/api/v1/alerts/{uuid.uuid4()}/resolve")
    assert response.status_code == 404


def _condition_payload(robot_id, condition_status, *, score=2.5, reason="scored"):
    as_of = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)
    return {
        "as_of": as_of,
        "window_start": as_of - timedelta(hours=168),
        "lookback_hours": 168,
        "condition_model_version": "rms-z-v1",
        "method": "rms_z_score",
        "predicts_failure": False,
        "robots": [
            {
                "robot_id": robot_id,
                "status": condition_status,
                "score": score,
                "reason": reason,
                "candidate_bucket_start": as_of - timedelta(hours=1),
            }
        ],
    }


def test_condition_sync_requires_operator_or_admin(
    unauthenticated_client, viewer_client, monkeypatch
):
    monkeypatch.setattr(
        "app.services.telemetry_condition_service.get_fleet_conditions",
        lambda *args, **kwargs: pytest.fail("condition service must not run before authorization"),
    )
    assert unauthenticated_client.post("/api/v1/alerts/sync-conditions").status_code == 401
    assert viewer_client.post("/api/v1/alerts/sync-conditions").status_code == 403


def test_condition_sync_creates_updates_and_deduplicates_alert(
    operator_client, db_session, monkeypatch
):
    _, _ = _seed_alerts(db_session)
    robot = db_session.query(Robot).filter(Robot.name == "Alert Robot").one()
    payload = _condition_payload(robot.id, "warning")
    monkeypatch.setattr(
        "app.services.telemetry_condition_service.get_fleet_conditions",
        lambda *args, **kwargs: payload,
    )

    created = operator_client.post("/api/v1/alerts/sync-conditions")
    assert created.status_code == 200
    created_body = created.json()
    assert datetime.fromisoformat(created_body.pop("as_of").replace("Z", "+00:00")) == payload["as_of"]
    assert created_body == {
        "lookback_hours": 168,
        "condition_model_version": "rms-z-v1",
        "method": "rms_z_score",
        "predicts_failure": False,
        "evaluated": 1,
        "created": 1,
        "updated": 0,
        "resolved": 0,
        "unchanged": 0,
        "unknown": 0,
    }
    repeated = operator_client.post("/api/v1/alerts/sync-conditions").json()
    assert repeated["created"] == 0
    assert repeated["unchanged"] == 1

    payload["robots"][0]["status"] = "critical"
    payload["robots"][0]["score"] = 4.25
    escalated = operator_client.post("/api/v1/alerts/sync-conditions").json()
    assert escalated["updated"] == 1
    alerts = db_session.query(Alert).filter(Alert.alert_type == "telemetry_condition").all()
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.CRITICAL
    assert "score=4.250" in alerts[0].message
    assert "not a failure prediction" in alerts[0].message


def test_condition_sync_resolves_only_normal_signal(operator_client, db_session, monkeypatch):
    _seed_alerts(db_session)
    robot = db_session.query(Robot).filter(Robot.name == "Alert Robot").one()
    existing = Alert(
        robot_id=robot.id,
        severity=AlertSeverity.WARNING,
        alert_type="telemetry_condition",
        message="Existing truthful condition alert.",
        triggered_at=datetime(2026, 9, 18, 10, tzinfo=timezone.utc),
    )
    db_session.add(existing)
    db_session.commit()

    payload = _condition_payload(robot.id, "unknown", score=None, reason="minimum_baseline_rows_not_met")
    monkeypatch.setattr(
        "app.services.telemetry_condition_service.get_fleet_conditions",
        lambda *args, **kwargs: payload,
    )
    unknown = operator_client.post("/api/v1/alerts/sync-conditions").json()
    db_session.refresh(existing)
    assert unknown["unknown"] == 1
    assert existing.resolved_at is None

    payload["robots"][0]["status"] = "normal"
    payload["robots"][0]["score"] = 0.5
    payload["robots"][0]["reason"] = "within_baseline"
    normal = operator_client.post("/api/v1/alerts/sync-conditions").json()
    db_session.refresh(existing)
    assert normal["resolved"] == 1
    assert existing.resolved_at == payload["as_of"]


def test_condition_sync_validates_lookback(operator_client):
    assert operator_client.post(
        "/api/v1/alerts/sync-conditions", params={"lookback_hours": 20}
    ).status_code == 422
