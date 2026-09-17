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
    site = Site(site_code=f"COND-S-{suffix}", name="Condition Test Site", timezone="UTC")
    model = RobotModel(
        model_code=f"COND-M-{suffix}", manufacturer="RoboOps", name="Condition Test Model", category="inspection"
    )
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code=f"COND-R-{suffix}", name="Condition Test Robot", serial_number=f"COND-SN-{suffix}",
        model_id=model.id, site_id=site.id, status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    battery = Sensor(robot_id=robot.id, sensor_code=f"COND-BAT-{suffix}", sensor_type=SensorType.BATTERY, unit="percent")
    temperature = Sensor(robot_id=robot.id, sensor_code=f"COND-TMP-{suffix}", sensor_type=SensorType.TEMPERATURE, unit="celsius")
    db_session.add_all([battery, temperature])
    db_session.commit()
    return robot, battery, temperature


def _reading(sensor, robot, recorded_at, value, event_id):
    return SensorReading(sensor_id=sensor.id, robot_id=robot.id, recorded_at=recorded_at, value=value, source_event_id=event_id)


def _add_bucket(db_session, robot, battery, temperature, bucket, suffix, battery_values, temperature_values):
    readings = []
    for minute, battery_value, temperature_value in zip((5, 25, 45), battery_values, temperature_values, strict=True):
        timestamp = bucket + timedelta(minutes=minute)
        readings.extend([
            _reading(battery, robot, timestamp, battery_value, f"cond-b-{suffix}-{bucket.isoformat()}-{minute}"),
            _reading(temperature, robot, timestamp, temperature_value, f"cond-t-{suffix}-{bucket.isoformat()}-{minute}"),
        ])
    db_session.add_all(readings)


def test_condition_service_uses_real_postgres_history_without_future_or_cross_robot_leakage(db_session):
    as_of = datetime(2026, 9, 16, 14, 59, tzinfo=timezone.utc)
    suffix = uuid.uuid4().hex[:8]
    robot, battery, temperature = _create_robot_with_sensors(db_session, suffix)
    robot_id = robot.id
    baseline_start = datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)

    for index in range(20):
        bucket = baseline_start + timedelta(hours=index)
        offset = float((index % 5) - 2)
        spread = 1.0 + float(index % 3)
        _add_bucket(
            db_session, robot, battery, temperature, bucket, f"{suffix}-{index}",
            (70.0 + offset - spread, 70.0 + offset, 70.0 + offset + spread),
            (30.0 + offset - spread, 30.0 + offset, 30.0 + offset + spread),
        )

    candidate_bucket = datetime(2026, 9, 16, 14, 0, tzinfo=timezone.utc)
    _add_bucket(db_session, robot, battery, temperature, candidate_bucket, f"{suffix}-candidate", (8.0, 10.0, 12.0), (54.0, 56.0, 58.0))

    other_suffix = uuid.uuid4().hex[:8]
    other_robot, other_battery, other_temperature = _create_robot_with_sensors(db_session, other_suffix)
    for index in range(20):
        _add_bucket(
            db_session, other_robot, other_battery, other_temperature,
            baseline_start + timedelta(hours=index), f"{other_suffix}-{index}",
            (1.0, 2.0, 3.0), (58.0, 59.0, 60.0),
        )

    future_bucket = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)
    _add_bucket(db_session, robot, battery, temperature, future_bucket, f"{suffix}-future", (-9999.0, -9998.0, -9997.0), (9997.0, 9998.0, 9999.0))
    db_session.commit()

    result = get_robot_condition(db_session, robot_id=robot_id, as_of=as_of, lookback_hours=24)

    assert result["robot_id"] == robot_id
    assert result["baseline_row_count"] == 20
    assert result["candidate_bucket_start"] == candidate_bucket
    assert result["status"] in {"warning", "critical"}
    assert result["score"] is not None and result["score"] >= 2.0
    assert set(result["feature_z_scores"]) == {"battery_mean", "battery_stddev", "temperature_mean", "temperature_stddev"}
    assert result["as_of"] == as_of
    assert result["window_start"] == as_of - timedelta(hours=24)
    assert result["condition_model_version"] == "rms-z-v1"
    assert result["method"] == "rms_z_score"
    assert result["predicts_failure"] is False
