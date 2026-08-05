"""API tests for the read-only fleet dashboard endpoints."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

from app.models.alert import Alert, AlertSeverity
from app.models.maintenance_record import MaintenanceRecord
from app.models.maintenance_schedule import MaintenanceSchedule, MaintenanceStatus
from app.models.robot import Robot, RobotStatus
from app.models.robot_model import RobotModel
from app.models.site import Site
from app.models.technician import Technician

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)


# ---------------------------------------------------------------------------
# ORM seeding helpers.
#
# There is no CRUD API for alerts, maintenance schedules, maintenance
# records, or technicians, so these tests create rows directly through the
# ORM using db_session, following the same pattern already used by
# test_sites_api.py::test_delete_site_conflict_when_referenced.
# ---------------------------------------------------------------------------


def _make_site(db_session, code, name="Test Site"):
    site = Site(site_code=code, name=name, timezone="UTC")
    db_session.add(site)
    db_session.commit()
    return site


def _make_robot_model(db_session, code="MDL-DASH1"):
    model = RobotModel(model_code=code, manufacturer="Acme", name="Scout", category="inspection")
    db_session.add(model)
    db_session.commit()
    return model


def _make_robot(db_session, code, site, model, status=RobotStatus.ACTIVE):
    robot = Robot(
        robot_code=code,
        name=f"Robot {code}",
        serial_number=f"SN-{code}",
        model_id=model.id,
        site_id=site.id,
        status=status,
        installed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    return robot


def _make_alert(
    db_session,
    robot,
    severity,
    created_at,
    resolved_at=None,
    alert_type="vibration_spike",
    message="Test alert",
):
    alert = Alert(
        robot_id=robot.id,
        severity=severity,
        alert_type=alert_type,
        message=message,
        triggered_at=created_at,
        resolved_at=resolved_at,
        created_at=created_at,
    )
    db_session.add(alert)
    db_session.commit()
    return alert


def _make_schedule(
    db_session, robot, scheduled_for, status=MaintenanceStatus.SCHEDULED, maintenance_type="inspection"
):
    schedule = MaintenanceSchedule(
        robot_id=robot.id,
        scheduled_for=scheduled_for,
        maintenance_type=maintenance_type,
        status=status,
    )
    db_session.add(schedule)
    db_session.commit()
    return schedule


def _make_technician(db_session, code="TCH-DASH1"):
    technician = Technician(
        technician_code=code, name="Test Technician", email=f"{code.lower()}@example.com"
    )
    db_session.add(technician)
    db_session.commit()
    return technician


def _make_record(db_session, robot, technician, performed_at, maintenance_type="inspection"):
    record = MaintenanceRecord(
        robot_id=robot.id,
        technician_id=technician.id,
        performed_at=performed_at,
        maintenance_type=maintenance_type,
    )
    db_session.add(record)
    db_session.commit()
    return record


def _seed_fleet(db_session):
    """Three sites (one with zero robots) and six robots covering every
    RobotStatus value: 2 active, 1 idle, 1 maintenance, 1 offline, 1
    decommissioned.
    """
    model = _make_robot_model(db_session)
    site1 = _make_site(db_session, "STE-DASH1", "Dash Site One")
    site2 = _make_site(db_session, "STE-DASH2", "Dash Site Two")
    site3 = _make_site(db_session, "STE-DASH3", "Dash Site Three")

    robots = {
        "r1": _make_robot(db_session, "RBT-DASH1", site1, model, RobotStatus.ACTIVE),
        "r2": _make_robot(db_session, "RBT-DASH2", site1, model, RobotStatus.IDLE),
        "r3": _make_robot(db_session, "RBT-DASH3", site1, model, RobotStatus.MAINTENANCE),
        "r4": _make_robot(db_session, "RBT-DASH4", site2, model, RobotStatus.OFFLINE),
        "r5": _make_robot(db_session, "RBT-DASH5", site2, model, RobotStatus.DECOMMISSIONED),
        "r6": _make_robot(db_session, "RBT-DASH6", site2, model, RobotStatus.ACTIVE),
    }
    sites = {"site1": site1, "site2": site2, "site3": site3}
    return sites, robots


# ---------------------------------------------------------------------------
# /api/v1/dashboard/summary
# ---------------------------------------------------------------------------


def test_dashboard_summary_empty_state(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_robots"] == 0
    assert body["active_robots"] == 0
    assert body["idle_robots"] == 0
    assert body["maintenance_robots"] == 0
    assert body["offline_robots"] == 0
    assert body["decommissioned_robots"] == 0
    assert body["total_sites"] == 0
    assert body["open_alerts"] == 0
    assert body["warning_alerts"] == 0
    assert body["critical_alerts"] == 0
    assert body["maintenance_due_count"] == 0
    assert body["maintenance_overdue_count"] == 0


def test_dashboard_summary_counts(client, db_session):
    _, robots = _seed_fleet(db_session)
    now = datetime.now(timezone.utc)

    # Unresolved alerts: 2 critical, 1 warning, 1 info (info has no
    # dedicated summary field, but still counts toward open_alerts).
    _make_alert(db_session, robots["r1"], AlertSeverity.CRITICAL, now - timedelta(minutes=5))
    _make_alert(db_session, robots["r2"], AlertSeverity.WARNING, now - timedelta(minutes=4))
    _make_alert(db_session, robots["r3"], AlertSeverity.INFO, now - timedelta(minutes=3))
    _make_alert(db_session, robots["r5"], AlertSeverity.CRITICAL, now - timedelta(minutes=2))
    # A resolved alert must not be counted in any open-alert field.
    _make_alert(
        db_session, robots["r4"], AlertSeverity.WARNING, now - timedelta(minutes=1), resolved_at=now
    )

    # One overdue (past), one due (future) maintenance schedule.
    _make_schedule(db_session, robots["r1"], now - timedelta(days=1), MaintenanceStatus.SCHEDULED)
    _make_schedule(db_session, robots["r2"], now + timedelta(days=1), MaintenanceStatus.IN_PROGRESS)

    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_robots"] == 6
    assert body["active_robots"] == 2
    assert body["idle_robots"] == 1
    assert body["maintenance_robots"] == 1
    assert body["offline_robots"] == 1
    assert body["decommissioned_robots"] == 1
    assert body["total_sites"] == 3
    assert body["open_alerts"] == 4
    assert body["warning_alerts"] == 1
    assert body["critical_alerts"] == 2
    assert body["maintenance_due_count"] == 1
    assert body["maintenance_overdue_count"] == 1


# ---------------------------------------------------------------------------
# /api/v1/dashboard/robot-status
# ---------------------------------------------------------------------------


def test_robot_status_zero_state(client):
    resp = client.get("/api/v1/dashboard/robot-status")
    assert resp.status_code == 200
    assert resp.json() == {
        "total_robots": 0,
        "active": 0,
        "idle": 0,
        "maintenance": 0,
        "offline": 0,
        "decommissioned": 0,
    }


def test_robot_status_breakdown_counts(client, db_session):
    _seed_fleet(db_session)
    resp = client.get("/api/v1/dashboard/robot-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_robots"] == 6
    assert body["active"] == 2
    assert body["idle"] == 1
    assert body["maintenance"] == 1
    assert body["offline"] == 1
    assert body["decommissioned"] == 1


# ---------------------------------------------------------------------------
# /api/v1/dashboard/site-summary
# ---------------------------------------------------------------------------


def test_site_summary_empty_state(client):
    resp = client.get("/api/v1/dashboard/site-summary")
    assert resp.status_code == 200
    assert resp.json() == []


def test_site_summary_includes_zero_robot_sites_and_order(client, db_session):
    _seed_fleet(db_session)
    resp = client.get("/api/v1/dashboard/site-summary")
    assert resp.status_code == 200
    body = resp.json()
    # Deterministic ordering: site_code ascending.
    assert [item["site_code"] for item in body] == ["STE-DASH1", "STE-DASH2", "STE-DASH3"]
    by_code = {item["site_code"]: item for item in body}
    assert by_code["STE-DASH1"]["robot_count"] == 3
    assert by_code["STE-DASH2"]["robot_count"] == 3
    assert by_code["STE-DASH3"]["robot_count"] == 0
    assert by_code["STE-DASH3"]["site_name"] == "Dash Site Three"


# ---------------------------------------------------------------------------
# /api/v1/dashboard/maintenance-summary
# ---------------------------------------------------------------------------


def test_maintenance_summary_empty_state(client):
    resp = client.get("/api/v1/dashboard/maintenance-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scheduled_count"] == 0
    assert body["in_progress_count"] == 0
    assert body["due_count"] == 0
    assert body["overdue_count"] == 0
    assert body["completed_count"] == 0
    assert "as_of" in body


def test_maintenance_summary_counts_and_boundary(client, db_session):
    model = _make_robot_model(db_session)
    site = _make_site(db_session, "STE-DASHM1", "Maintenance Site")
    robot = _make_robot(db_session, "RBT-DASHM1", site, model, RobotStatus.ACTIVE)
    technician = _make_technician(db_session)
    before_request = datetime.now(timezone.utc)

    # The service resolves its own as_of = utcnow() inside the request, so
    # exact-boundary equality can't be tested from here. Offsets of 1+ days
    # are used instead, safely clear of any timing race with the request.
    _make_schedule(db_session, robot, before_request - timedelta(days=1), MaintenanceStatus.SCHEDULED)  # overdue
    _make_schedule(db_session, robot, before_request + timedelta(days=1), MaintenanceStatus.IN_PROGRESS)  # due
    _make_schedule(db_session, robot, before_request + timedelta(days=2), MaintenanceStatus.SCHEDULED)  # due
    _make_schedule(db_session, robot, before_request - timedelta(days=2), MaintenanceStatus.CANCELLED)  # excluded
    _make_schedule(db_session, robot, before_request - timedelta(days=3), MaintenanceStatus.COMPLETED)  # excluded
    _make_record(db_session, robot, technician, before_request - timedelta(days=5))
    _make_record(db_session, robot, technician, before_request - timedelta(days=10))

    resp = client.get("/api/v1/dashboard/maintenance-summary")
    after_request = datetime.now(timezone.utc)
    assert resp.status_code == 200
    body = resp.json()
    assert body["scheduled_count"] == 2
    assert body["in_progress_count"] == 1
    assert body["due_count"] == 2
    assert body["overdue_count"] == 1
    assert body["completed_count"] == 2
    as_of = datetime.fromisoformat(body["as_of"].replace("Z", "+00:00"))
    assert before_request <= as_of <= after_request


# ---------------------------------------------------------------------------
# /api/v1/dashboard/latest-alerts
# ---------------------------------------------------------------------------


def test_latest_alerts_empty_state(client):
    resp = client.get("/api/v1/dashboard/latest-alerts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_latest_alerts_ordering_and_robot_details(client, db_session):
    model = _make_robot_model(db_session)
    site = _make_site(db_session, "STE-DASHA1", "Alerts Site")
    robot_a = _make_robot(db_session, "RBT-DASHA1", site, model, RobotStatus.ACTIVE)
    robot_b = _make_robot(db_session, "RBT-DASHA2", site, model, RobotStatus.ACTIVE)
    base = datetime.now(timezone.utc) - timedelta(hours=1)

    oldest = _make_alert(
        db_session, robot_a, AlertSeverity.INFO, base, alert_type="battery_low", message="Oldest"
    )
    middle = _make_alert(
        db_session,
        robot_b,
        AlertSeverity.WARNING,
        base + timedelta(minutes=10),
        alert_type="temp_high",
        message="Middle",
    )
    newest = _make_alert(
        db_session,
        robot_a,
        AlertSeverity.CRITICAL,
        base + timedelta(minutes=20),
        alert_type="collision",
        message="Newest",
    )

    resp = client.get("/api/v1/dashboard/latest-alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert [item["id"] for item in body] == [str(newest.id), str(middle.id), str(oldest.id)]

    newest_item = body[0]
    assert newest_item["robot_id"] == str(robot_a.id)
    assert newest_item["robot_code"] == "RBT-DASHA1"
    assert newest_item["robot_name"] == "Robot RBT-DASHA1"
    assert newest_item["severity"] == "critical"
    assert newest_item["alert_type"] == "collision"
    assert newest_item["message"] == "Newest"
    assert newest_item["sensor_id"] is None
    assert "site_id" not in newest_item
    assert "site_code" not in newest_item
    assert "site_name" not in newest_item


def test_latest_alerts_tiebreaker_by_id(client, db_session):
    model = _make_robot_model(db_session)
    site = _make_site(db_session, "STE-DASHA2", "Alerts Tie Site")
    robot = _make_robot(db_session, "RBT-DASHA3", site, model, RobotStatus.ACTIVE)
    same_instant = datetime.now(timezone.utc) - timedelta(minutes=1)

    first = _make_alert(db_session, robot, AlertSeverity.INFO, same_instant, alert_type="a", message="A")
    second = _make_alert(db_session, robot, AlertSeverity.INFO, same_instant, alert_type="b", message="B")
    expected_order = sorted([first, second], key=lambda a: a.id, reverse=True)

    resp = client.get("/api/v1/dashboard/latest-alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert [item["id"] for item in body] == [str(a.id) for a in expected_order]


def test_latest_alerts_default_limit(client, db_session):
    model = _make_robot_model(db_session)
    site = _make_site(db_session, "STE-DASHA3", "Alerts Limit Site")
    robot = _make_robot(db_session, "RBT-DASHA4", site, model, RobotStatus.ACTIVE)
    base = datetime.now(timezone.utc) - timedelta(hours=1)
    for i in range(12):
        _make_alert(
            db_session, robot, AlertSeverity.INFO, base + timedelta(minutes=i), alert_type="x", message=f"Alert {i}"
        )

    resp = client.get("/api/v1/dashboard/latest-alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    assert body[0]["message"] == "Alert 11"
    assert body[-1]["message"] == "Alert 2"


def test_latest_alerts_custom_limit(client, db_session):
    model = _make_robot_model(db_session)
    site = _make_site(db_session, "STE-DASHA4", "Alerts Custom Limit Site")
    robot = _make_robot(db_session, "RBT-DASHA5", site, model, RobotStatus.ACTIVE)
    base = datetime.now(timezone.utc) - timedelta(hours=1)
    for i in range(5):
        _make_alert(
            db_session, robot, AlertSeverity.INFO, base + timedelta(minutes=i), alert_type="x", message=f"Alert {i}"
        )

    resp = client.get("/api/v1/dashboard/latest-alerts", params={"limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert [item["message"] for item in body] == ["Alert 4", "Alert 3", "Alert 2"]


def test_latest_alerts_invalid_limit_returns_422(client):
    assert client.get("/api/v1/dashboard/latest-alerts", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/dashboard/latest-alerts", params={"limit": 101}).status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/dashboard/health-summary
# ---------------------------------------------------------------------------


def test_health_summary_empty_state(client):
    resp = client.get("/api/v1/dashboard/health-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["average_health_value"] is None
    assert body["health_metric_available"] is False
    assert body["robot_status_counts"] == {
        "total_robots": 0,
        "active": 0,
        "idle": 0,
        "maintenance": 0,
        "offline": 0,
        "decommissioned": 0,
    }
    assert body["maintenance_due_count"] == 0
    assert body["maintenance_overdue_count"] == 0


def test_health_summary_counts(client, db_session):
    _, robots = _seed_fleet(db_session)
    now = datetime.now(timezone.utc)
    _make_schedule(db_session, robots["r1"], now - timedelta(days=1), MaintenanceStatus.SCHEDULED)  # overdue
    _make_schedule(db_session, robots["r2"], now + timedelta(days=1), MaintenanceStatus.IN_PROGRESS)  # due

    resp = client.get("/api/v1/dashboard/health-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["average_health_value"] is None
    assert body["health_metric_available"] is False
    assert body["robot_status_counts"] == {
        "total_robots": 6,
        "active": 2,
        "idle": 1,
        "maintenance": 1,
        "offline": 1,
        "decommissioned": 1,
    }
    assert body["maintenance_due_count"] == 1
    assert body["maintenance_overdue_count"] == 1
