from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import (
    Robot,
    RobotModel,
    RobotStatus,
    Sensor,
    SensorReading,
    SensorType,
    Site,
)
from app.routers import dashboard as dashboard_router
from app.services.telemetry_anomaly_service import MAX_ANOMALY_EVENTS


pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not set.",
)


def test_telemetry_anomalies_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get(
        "/api/v1/dashboard/telemetry-anomalies"
    )

    assert response.status_code == 401


def test_telemetry_anomalies_authenticated(client, monkeypatch):
    expected = {
        "as_of": "2026-09-11T12:00:00Z",
        "window_start": "2026-09-10T12:00:00Z",
        "lookback_hours": 24,
        "total_readings": 3,
        "severity_counts": {
            "normal": 1,
            "warning": 1,
            "critical": 1,
            "unknown": 0,
        },
        "reason_counts": {
            "battery_low": 1,
            "temperature_critical": 1,
        },
        "anomaly_events": [],
        "anomaly_event_limit": MAX_ANOMALY_EVENTS,
        "anomaly_events_truncated": False,
    }

    monkeypatch.setattr(
        dashboard_router.telemetry_anomaly_service,
        "get_anomaly_summary",
        lambda db, lookback_hours=24: expected,
    )

    response = client.get(
        "/api/v1/dashboard/telemetry-anomalies"
    )

    assert response.status_code == 200

    body = response.json()
    assert body["lookback_hours"] == 24
    assert body["total_readings"] == 3
    assert body["severity_counts"]["critical"] == 1
    assert body["anomaly_event_limit"] == MAX_ANOMALY_EVENTS
    assert body["anomaly_events_truncated"] is False


def test_telemetry_anomalies_validates_lookback(client):
    response = client.get(
        "/api/v1/dashboard/telemetry-anomalies?lookback_hours=0"
    )

    assert response.status_code == 422


def test_telemetry_anomalies_real_query_path(client, db_session):
    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[:8]

    site = Site(
        site_code=f"AN-{suffix}",
        name="Anomaly Site",
        timezone="UTC",
    )
    model = RobotModel(
        model_code=f"AM-{suffix}",
        manufacturer="Acme",
        name="Anomaly Scout",
        category="inspection",
    )
    db_session.add_all([site, model])
    db_session.commit()

    robot = Robot(
        robot_code=f"AR-{suffix}",
        name="Anomaly Robot",
        serial_number=f"AS-{suffix}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()

    battery = Sensor(
        robot_id=robot.id,
        sensor_code=f"AN-BAT-{suffix}",
        sensor_type=SensorType.BATTERY,
        unit="percent",
    )
    temperature = Sensor(
        robot_id=robot.id,
        sensor_code=f"AN-TEMP-{suffix}",
        sensor_type=SensorType.TEMPERATURE,
        unit="celsius",
    )
    vibration = Sensor(
        robot_id=robot.id,
        sensor_code=f"AN-VIB-{suffix}",
        sensor_type=SensorType.VIBRATION,
        unit="mm/s",
    )
    db_session.add_all([battery, temperature, vibration])
    db_session.commit()

    readings = [
        SensorReading(
            sensor_id=battery.id,
            robot_id=robot.id,
            recorded_at=now - timedelta(minutes=5),
            value=80.0,
            source_event_id=f"an-normal-{suffix}",
        ),
        SensorReading(
            sensor_id=battery.id,
            robot_id=robot.id,
            recorded_at=now - timedelta(minutes=10),
            value=20.0,
            source_event_id=f"an-warning-{suffix}",
        ),
        SensorReading(
            sensor_id=temperature.id,
            robot_id=robot.id,
            recorded_at=now - timedelta(minutes=15),
            value=58.0,
            source_event_id=f"an-critical-{suffix}",
        ),
        SensorReading(
            sensor_id=vibration.id,
            robot_id=robot.id,
            recorded_at=now - timedelta(minutes=20),
            value=8.0,
            source_event_id=f"an-unsupported-{suffix}",
        ),
        SensorReading(
            sensor_id=battery.id,
            robot_id=robot.id,
            recorded_at=now - timedelta(hours=25),
            value=10.0,
            source_event_id=f"an-outside-{suffix}",
        ),
    ]
    db_session.add_all(readings)
    db_session.commit()

    response = client.get(
        "/api/v1/dashboard/telemetry-anomalies?lookback_hours=24"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lookback_hours"] == 24
    assert body["total_readings"] == 3
    assert body["severity_counts"] == {
        "normal": 1,
        "warning": 1,
        "critical": 1,
        "unknown": 0,
    }
    assert body["reason_counts"] == {
        "battery_low": 1,
        "temperature_critical": 1,
    }
    assert body["anomaly_event_limit"] == MAX_ANOMALY_EVENTS
    assert body["anomaly_events_truncated"] is False

    events = body["anomaly_events"]
    assert len(events) == 2
    assert [event["severity"] for event in events] == ["warning", "critical"]
    assert [event["reason"] for event in events] == [
        "battery_low",
        "temperature_critical",
    ]
    assert events[0]["recorded_at"] > events[1]["recorded_at"]
