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
from app.services.telemetry_trend_service import MAX_TREND_POINTS


pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not set.",
)


def test_telemetry_trends_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/dashboard/telemetry-trends")
    assert response.status_code == 401


def test_telemetry_trends_validates_lookback(client):
    response = client.get(
        "/api/v1/dashboard/telemetry-trends?lookback_hours=0"
    )
    assert response.status_code == 422


def test_telemetry_trends_rejects_invalid_robot_uuid(client):
    response = client.get(
        "/api/v1/dashboard/telemetry-trends?robot_id=not-a-uuid"
    )
    assert response.status_code == 422


def test_telemetry_trends_real_query_path(client, db_session):
    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[:8]

    site = Site(
        site_code=f"TR-{suffix}",
        name="Trend Site",
        timezone="UTC",
    )
    model = RobotModel(
        model_code=f"TM-{suffix}",
        manufacturer="Acme",
        name="Trend Scout",
        category="inspection",
    )
    db_session.add_all([site, model])
    db_session.commit()

    robot = Robot(
        robot_code=f"RR-{suffix}",
        name="Trend Robot",
        serial_number=f"RS-{suffix}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    other_robot = Robot(
        robot_code=f"OR-{suffix}",
        name="Other Robot",
        serial_number=f"OS-{suffix}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add_all([robot, other_robot])
    db_session.commit()

    battery = Sensor(
        robot_id=robot.id,
        sensor_code=f"TR-BAT-{suffix}",
        sensor_type=SensorType.BATTERY,
        unit="percent",
    )
    temperature = Sensor(
        robot_id=robot.id,
        sensor_code=f"TR-TMP-{suffix}",
        sensor_type=SensorType.TEMPERATURE,
        unit="celsius",
    )
    vibration = Sensor(
        robot_id=robot.id,
        sensor_code=f"TR-VIB-{suffix}",
        sensor_type=SensorType.VIBRATION,
        unit="mm/s",
    )
    other_battery = Sensor(
        robot_id=other_robot.id,
        sensor_code=f"OT-BAT-{suffix}",
        sensor_type=SensorType.BATTERY,
        unit="percent",
    )
    db_session.add_all([battery, temperature, vibration, other_battery])
    db_session.commit()

    db_session.add_all(
        [
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=30),
                value=70.0,
                source_event_id=f"trend-bat-1-{suffix}",
            ),
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=20),
                value=60.0,
                source_event_id=f"trend-bat-2-{suffix}",
            ),
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=10),
                value=50.0,
                source_event_id=f"trend-bat-3-{suffix}",
            ),
            SensorReading(
                sensor_id=temperature.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=25),
                value=30.0,
                source_event_id=f"trend-temp-1-{suffix}",
            ),
            SensorReading(
                sensor_id=temperature.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=5),
                value=40.0,
                source_event_id=f"trend-temp-2-{suffix}",
            ),
            SensorReading(
                sensor_id=vibration.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=15),
                value=9.0,
                source_event_id=f"trend-vib-{suffix}",
            ),
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(hours=25),
                value=10.0,
                source_event_id=f"trend-old-{suffix}",
            ),
            SensorReading(
                sensor_id=other_battery.id,
                robot_id=other_robot.id,
                recorded_at=now - timedelta(minutes=10),
                value=90.0,
                source_event_id=f"trend-other-{suffix}",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/dashboard/telemetry-trends?lookback_hours=24&robot_id={robot.id}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lookback_hours"] == 24
    assert body["robot_id"] == str(robot.id)
    assert body["total_readings"] == 5
    assert body["series_count"] == 2
    assert body["point_limit"] == MAX_TREND_POINTS
    assert body["points_truncated"] is False

    by_type = {series["sensor_type"]: series for series in body["series"]}
    assert set(by_type) == {"battery", "temperature"}

    battery_series = by_type["battery"]
    assert battery_series["reading_count"] == 3
    assert battery_series["min_value"] == 50.0
    assert battery_series["max_value"] == 70.0
    assert battery_series["avg_value"] == 60.0
    assert battery_series["latest_value"] == 50.0
    assert [point["value"] for point in battery_series["points"]] == [70.0, 60.0, 50.0]
    assert battery_series["points"][0]["recorded_at"] < battery_series["points"][-1]["recorded_at"]

    temperature_series = by_type["temperature"]
    assert temperature_series["reading_count"] == 2
    assert temperature_series["min_value"] == 30.0
    assert temperature_series["max_value"] == 40.0
    assert temperature_series["avg_value"] == 35.0
    assert temperature_series["latest_value"] == 40.0
    assert [point["value"] for point in temperature_series["points"]] == [30.0, 40.0]
