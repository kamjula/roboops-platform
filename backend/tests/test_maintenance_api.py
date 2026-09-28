"""Maintenance read contract and viewer access."""
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.models.maintenance_schedule import MaintenanceStatus
from test_dashboard_api import (
    _make_record, _make_robot, _make_robot_model, _make_schedule, _make_site, _make_technician,
)

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set.")


def test_maintenance_empty_and_login_required(client, unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/maintenance").status_code == 401
    body = client.get("/api/v1/maintenance").json()
    assert body["schedules"] == body["records"] == []
    assert body["schedule_total"] == body["record_total"] == 0
    assert body["as_of"]


def test_maintenance_viewer_reads_ordered_bounded_records(viewer_client, db_session):
    site = _make_site(db_session, "STE-MAINT1")
    model = _make_robot_model(db_session, "MDL-MAINT1")
    robot = _make_robot(db_session, "RB-MAINT1", site, model)
    technician = _make_technician(db_session, "TCH-MAINT1")
    now = datetime.now(timezone.utc)
    _make_schedule(db_session, robot, now + timedelta(days=2), MaintenanceStatus.SCHEDULED)
    earlier = _make_schedule(db_session, robot, now - timedelta(days=2), MaintenanceStatus.COMPLETED)
    _make_record(db_session, robot, technician, now - timedelta(days=3))
    latest = _make_record(db_session, robot, technician, now - timedelta(days=1))

    response = viewer_client.get("/api/v1/maintenance?limit=1")
    assert response.status_code == 200
    body = response.json()
    assert (body["schedule_total"], body["record_total"]) == (2, 2)
    assert body["schedules"][0]["id"] == str(earlier.id)
    assert body["schedules"][0]["robot_code"] == "RB-MAINT1"
    assert body["records"][0]["id"] == str(latest.id)
    assert body["records"][0]["technician_name"] == "Test Technician"
    assert viewer_client.get("/api/v1/maintenance?limit=201").status_code == 422
