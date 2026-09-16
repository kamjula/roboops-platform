"""Feature extraction for predictive-maintenance ML from persisted telemetry.

This module intentionally does not create synthetic labels or claim model
accuracy. It produces time-windowed feature rows from real SensorReading data
so later training code has a reproducible, leakage-aware source dataset.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Sensor, SensorReading, SensorType

SUPPORTED_SENSOR_TYPES = (SensorType.BATTERY, SensorType.TEMPERATURE)
DEFAULT_LOOKBACK_HOURS = 168
MIN_SAMPLES_PER_SENSOR = 3


def _normalize_as_of(as_of: datetime | None) -> datetime:
    value = as_of or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_predictive_feature_dataset(
    db: Session,
    *,
    as_of: datetime | None = None,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    robot_id: uuid.UUID | None = None,
    min_samples_per_sensor: int = MIN_SAMPLES_PER_SENSOR,
) -> dict:
    """Build hourly battery/temperature features from persisted telemetry.

    Feature rows contain only information available inside each historical
    hour. No future values are joined into a bucket and no maintenance/failure
    label is manufactured. Buckets missing the minimum number of readings for
    either supported sensor are reported as incomplete and excluded from the
    trainable feature rows.
    """
    if lookback_hours < 1:
        raise ValueError("lookback_hours must be at least 1")
    if min_samples_per_sensor < 1:
        raise ValueError("min_samples_per_sensor must be at least 1")

    as_of = _normalize_as_of(as_of)
    window_start = as_of - timedelta(hours=lookback_hours)
    bucket_start = func.date_trunc("hour", SensorReading.recorded_at).label("bucket_start")

    battery = Sensor.sensor_type == SensorType.BATTERY
    temperature = Sensor.sensor_type == SensorType.TEMPERATURE

    statement = (
        select(
            SensorReading.robot_id,
            bucket_start,
            func.count(SensorReading.id).filter(battery).label("battery_count"),
            func.avg(SensorReading.value).filter(battery).label("battery_mean"),
            func.min(SensorReading.value).filter(battery).label("battery_min"),
            func.max(SensorReading.value).filter(battery).label("battery_max"),
            func.stddev_samp(SensorReading.value).filter(battery).label("battery_stddev"),
            func.count(SensorReading.id).filter(temperature).label("temperature_count"),
            func.avg(SensorReading.value).filter(temperature).label("temperature_mean"),
            func.min(SensorReading.value).filter(temperature).label("temperature_min"),
            func.max(SensorReading.value).filter(temperature).label("temperature_max"),
            func.stddev_samp(SensorReading.value).filter(temperature).label("temperature_stddev"),
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(
            Sensor.sensor_type.in_(SUPPORTED_SENSOR_TYPES),
            SensorReading.recorded_at >= window_start,
            SensorReading.recorded_at <= as_of,
        )
        .group_by(SensorReading.robot_id, bucket_start)
        .order_by(SensorReading.robot_id, bucket_start)
    )
    if robot_id is not None:
        statement = statement.where(SensorReading.robot_id == robot_id)

    feature_rows: list[dict] = []
    incomplete_bucket_count = 0
    total_bucket_count = 0

    for row in db.execute(statement):
        total_bucket_count += 1
        battery_count = int(row.battery_count or 0)
        temperature_count = int(row.temperature_count or 0)
        if battery_count < min_samples_per_sensor or temperature_count < min_samples_per_sensor:
            incomplete_bucket_count += 1
            continue

        feature_rows.append(
            {
                "robot_id": row.robot_id,
                "bucket_start": row.bucket_start,
                "battery_count": battery_count,
                "battery_mean": float(row.battery_mean),
                "battery_min": float(row.battery_min),
                "battery_max": float(row.battery_max),
                "battery_stddev": (
                    float(row.battery_stddev) if row.battery_stddev is not None else 0.0
                ),
                "temperature_count": temperature_count,
                "temperature_mean": float(row.temperature_mean),
                "temperature_min": float(row.temperature_min),
                "temperature_max": float(row.temperature_max),
                "temperature_stddev": (
                    float(row.temperature_stddev) if row.temperature_stddev is not None else 0.0
                ),
            }
        )

    return {
        "as_of": as_of,
        "window_start": window_start,
        "lookback_hours": lookback_hours,
        "robot_id": robot_id,
        "min_samples_per_sensor": min_samples_per_sensor,
        "total_bucket_count": total_bucket_count,
        "complete_feature_row_count": len(feature_rows),
        "incomplete_bucket_count": incomplete_bucket_count,
        "supported_sensor_types": [sensor_type.value for sensor_type in SUPPORTED_SENSOR_TYPES],
        "supervised_failure_labels_available": False,
        "supervised_label_reason": (
            "maintenance_records do not currently contain a verified failure outcome label"
        ),
        "feature_rows": feature_rows,
    }
