from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Robot, RobotModel, RobotStatus, Sensor, SensorReading, SensorType, Site
from app.services.telemetry_condition_service import get_robot_condition

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)


def _create_robot_with_sensors(db_session, suffix: str):
    site = Site(site_code=f"COND-S-{suffix}", name="Condition Site", timezone="UTC")
    model = RobotModel(
        model_code=f"COND-M-{suffix}",
        manufacturer="RoboOps",
        name="Condition Model",
        category="inspection",
    )
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code=f"COND-R-{suffix}",
        name="Condition Robot",
        serial_number=f"COND-SN-{suffix}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    battery = Sensor(robot_id=robot.id, sensor_code=f"COND-B-{suffix}", sensor_type=SensorType.BATTERY, unit="percent")
    temperature = Sensor(robot_id=robot.id, sensor_code=f"COND-T-{suffix}", sensor_type=SensorType.TEMPERATURE, unit="celsius")
    db_session.add_all([battery, temperature])
    db_session.commit()
    return robot, battery, temperature


def _add_hour(db_session, robot, battery, temperature, bucket, index, battery_value, temperature_value):
    for minute, delta in ((5, -0.5), (25, 0.0), (45, 0.5)):
        timestamp = bucket + timedelta(minutes=minute)
        db_session.add_all([
            SensorReading(sensor_id=battery.id, robot_id=robot.id, recorded_at=timestamp, value=battery_value + delta, source_event_id=f"cond-b-{robot.id}-{index}-{minute}"),
            SensorReading(sensor_id=temperature.id, robot_id=robot.id, recorded_at=timestamp, value=temperature_value + delta, source_event_id=f"cond-t-{robot.id}-{index}-{minute}"),
        ])


def test_condition_service_uses_prior_persisted_history_without_cross_robot_or_future_leakage(db_session):
    as_of = datetime(2026, 9, 16, 14, 59, tzinfo=timezone.utc)
    suffix = uuid.uuid4().hex[:8]
    robot, battery, temperature = _create_robot_with_sensors(db_session, suffix)
    other, other_battery, other_temperature = _create_robot_with_sensors(db_session, f"o{suffix}")

    start = datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)
    # Twenty complete prior buckets with real variation form the baseline.
    for index in range(20):
        bucket = start + timedelta(hours=index)
        _add_hour(db_session, robot, battery, temperature, bucket, index, 70.0 + index * 0.2, 30.0 + index * 0.1)

    # Latest complete bucket is the candidate and is deliberately unusual.
    candidate_bucket = start + timedelta(hours=20)
    _add_hour(db_session, robot, battery, temperature, candidate_bucket, 20, 40.0, 50.0)

    # Another robot has extreme values in the same window; robot scoping must isolate them.
    _add_hour(db_session, other, other_battery, other_temperature, candidate_bucket, 0, 1.0, 59.0)

    # Future complete telemetry must not become the candidate or baseline.
    future_bucket = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)
    _add_hour(db_session, robot, battery, temperature, future_bucket, 99, 99.0, 10.0)
    db_session.commit()

    result = get_robot_condition(
        db_session,
        robot_id=robot.id,
        as_of=as_of,
        lookback_hours=24,
    )

    assert result["robot_id"] == robot.id
    assert result["baseline_row_count"] == 20
    assert result["candidate_bucket_start"] == candidate_bucket
    assert result["status"] == "critical"
    assert result["score"] is not None and result["score"] >= 3.0
    assert result["predicts_failure"] is False
    assert result["method"] == "rms_z_score"
