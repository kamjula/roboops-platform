from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Robot, RobotModel, RobotStatus, Sensor, SensorReading, SensorType, Site

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set.")


def test_robot_health_is_authenticated_set_based_and_explicit(client, db_session):
    site = Site(site_code=f"HEALTH-{uuid.uuid4().hex[:8]}", name="Health Site", timezone="UTC")
    model = RobotModel(model_code=f"HEALTH-MODEL-{uuid.uuid4().hex[:8]}", manufacturer="Acme", name="Scout", category="inspection")
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code=f"HR-{uuid.uuid4().hex[:8]}",
        name="Health Robot",
        serial_number=f"HS-{uuid.uuid4().hex[:8]}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.MAINTENANCE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    battery = Sensor(robot_id=robot.id, sensor_code=f"{robot.robot_code}-BATTERY", sensor_type=SensorType.BATTERY, unit="percent")
    temperature = Sensor(robot_id=robot.id, sensor_code=f"{robot.robot_code}-TEMP", sensor_type=SensorType.TEMPERATURE, unit="celsius")
    db_session.add_all([battery, temperature])
    db_session.commit()
    db_session.add(SensorReading(
        sensor_id=battery.id,
        robot_id=robot.id,
        recorded_at=datetime.now(timezone.utc) - timedelta(seconds=30),
        value=22,
        source_event_id="health-api-battery",
    ))
    db_session.add(SensorReading(
        sensor_id=temperature.id,
        robot_id=robot.id,
        recorded_at=datetime.now(timezone.utc) - timedelta(seconds=30),
        value=35,
        source_event_id="health-api-temperature",
    ))
    db_session.commit()

    response = client.get("/api/v1/dashboard/robot-health")
    assert response.status_code == 200
    body = response.json()
    assert body["freshness_threshold_seconds"] == 300
    assert len(body["robots"]) == 1
    item = body["robots"][0]
    assert item["operational_status"] == "maintenance"
    assert item["health_state"] == "warning"
    assert item["reason_codes"] == ["battery_low", "robot_in_maintenance"]
    assert item["battery"]["freshness"] == "fresh"
    assert item["temperature"]["state"] == "healthy"