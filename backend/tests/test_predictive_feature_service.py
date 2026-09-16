from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Robot, RobotModel, RobotStatus, Sensor, SensorReading, SensorType, Site
from app.services.predictive_feature_service import build_predictive_feature_dataset

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)


def _create_robot_with_sensors(db_session, suffix: str):
    site = Site(site_code=f"ML-S-{suffix}", name="ML Feature Site", timezone="UTC")
    model = RobotModel(
        model_code=f"ML-M-{suffix}",
        manufacturer="RoboOps",
        name="Feature Model",
        category="inspection",
    )
    db_session.add_all([site, model])
    db_session.commit()

    robot = Robot(
        robot_code=f"ML-R-{suffix}",
        name="Feature Robot",
        serial_number=f"ML-SN-{suffix}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()

    battery = Sensor(
        robot_id=robot.id,
        sensor_code=f"ML-BAT-{suffix}",
        sensor_type=SensorType.BATTERY,
        unit="percent",
    )
    temperature = Sensor(
        robot_id=robot.id,
        sensor_code=f"ML-TMP-{suffix}",
        sensor_type=SensorType.TEMPERATURE,
        unit="celsius",
    )
    db_session.add_all([battery, temperature])
    db_session.commit()
    return robot, battery, temperature


def _reading(sensor, robot, recorded_at, value, event_id):
    return SensorReading(
        sensor_id=sensor.id,
        robot_id=robot.id,
        recorded_at=recorded_at,
        value=value,
        source_event_id=event_id,
    )


def test_build_predictive_feature_dataset_uses_persisted_hourly_telemetry(db_session):
    as_of = datetime(2026, 9, 16, 14, 59, tzinfo=timezone.utc)
    suffix = uuid.uuid4().hex[:8]
    robot, battery, temperature = _create_robot_with_sensors(db_session, suffix)
    robot_id = robot.id

    readings = []
    # Complete 13:00 UTC feature bucket: three real persisted readings per sensor.
    for minute, battery_value, temperature_value in [
        (5, 80.0, 30.0),
        (25, 78.0, 32.0),
        (45, 76.0, 34.0),
    ]:
        timestamp = datetime(2026, 9, 16, 13, minute, tzinfo=timezone.utc)
        readings.extend(
            [
                _reading(battery, robot, timestamp, battery_value, f"ml-b-{suffix}-{minute}"),
                _reading(
                    temperature,
                    robot,
                    timestamp,
                    temperature_value,
                    f"ml-t-{suffix}-{minute}",
                ),
            ]
        )

    # Incomplete 12:00 UTC bucket: battery only, so it must not become a feature row.
    for minute, value in [(10, 70.0), (20, 69.0), (30, 68.0)]:
        readings.append(
            _reading(
                battery,
                robot,
                datetime(2026, 9, 16, 12, minute, tzinfo=timezone.utc),
                value,
                f"ml-incomplete-{suffix}-{minute}",
            )
        )

    # A future reading must not leak into the dataset.
    readings.append(
        _reading(
            battery,
            robot,
            as_of + timedelta(minutes=5),
            -9999.0,
            f"ml-future-{suffix}",
        )
    )
    db_session.add_all(readings)
    db_session.commit()

    dataset = build_predictive_feature_dataset(
        db_session,
        as_of=as_of,
        lookback_hours=4,
        robot_id=robot_id,
        min_samples_per_sensor=3,
    )

    assert dataset["robot_id"] == robot_id
    assert dataset["total_bucket_count"] == 2
    assert dataset["complete_feature_row_count"] == 1
    assert dataset["incomplete_bucket_count"] == 1
    assert dataset["supervised_failure_labels_available"] is False

    row = dataset["feature_rows"][0]
    assert row["robot_id"] == robot_id
    assert row["bucket_start"] == datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)
    assert row["battery_count"] == 3
    assert row["battery_mean"] == pytest.approx(78.0)
    assert row["battery_min"] == pytest.approx(76.0)
    assert row["battery_max"] == pytest.approx(80.0)
    assert row["temperature_count"] == 3
    assert row["temperature_mean"] == pytest.approx(32.0)
    assert row["temperature_min"] == pytest.approx(30.0)
    assert row["temperature_max"] == pytest.approx(34.0)


def test_predictive_feature_dataset_validates_configuration(db_session):
    with pytest.raises(ValueError, match="lookback_hours"):
        build_predictive_feature_dataset(db_session, lookback_hours=0)

    with pytest.raises(ValueError, match="min_samples_per_sensor"):
        build_predictive_feature_dataset(db_session, min_samples_per_sensor=0)
