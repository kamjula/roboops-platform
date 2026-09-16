"""Statistical anomaly detection using persisted telemetry history."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.models import Sensor, SensorReading
from app.services.statistical_anomaly_policy import score_observation

SUPPORTED_SENSOR_TYPES = ("battery", "temperature")
DEFAULT_BASELINE_HOURS = 24


def get_statistical_anomalies(
    db: Session,
    *,
    as_of: datetime | None = None,
    baseline_hours: int = DEFAULT_BASELINE_HOURS,
    robot_id: uuid.UUID | None = None,
) -> dict:
    """Score each sensor's latest persisted reading against preceding history.

    PostgreSQL computes the historical baseline for all selected sensors in one
    set-based query. The latest reading itself is excluded from the aggregate,
    preserving the original no-leakage semantics without issuing one baseline
    query per sensor.
    """
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    else:
        as_of = as_of.astimezone(timezone.utc)
    window_start = as_of - timedelta(hours=baseline_hours)

    latest_stmt = (
        select(
            SensorReading.id.label("reading_id"),
            SensorReading.robot_id,
            SensorReading.sensor_id,
            Sensor.sensor_type,
            SensorReading.value,
            SensorReading.recorded_at,
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(
            Sensor.sensor_type.in_(SUPPORTED_SENSOR_TYPES),
            SensorReading.recorded_at >= window_start,
            SensorReading.recorded_at <= as_of,
        )
        .order_by(
            SensorReading.sensor_id,
            SensorReading.recorded_at.desc(),
            SensorReading.id.desc(),
        )
        .distinct(SensorReading.sensor_id)
        .subquery("latest_readings")
    )

    baseline_reading = aliased(SensorReading)
    statement = (
        select(
            latest_stmt.c.reading_id,
            latest_stmt.c.robot_id,
            latest_stmt.c.sensor_id,
            latest_stmt.c.sensor_type,
            latest_stmt.c.value,
            latest_stmt.c.recorded_at,
            func.count(baseline_reading.id).label("sample_count"),
            func.avg(baseline_reading.value).label("mean"),
            func.stddev_samp(baseline_reading.value).label("stddev"),
        )
        .outerjoin(
            baseline_reading,
            and_(
                baseline_reading.sensor_id == latest_stmt.c.sensor_id,
                baseline_reading.recorded_at >= window_start,
                baseline_reading.recorded_at < latest_stmt.c.recorded_at,
            ),
        )
        .group_by(
            latest_stmt.c.reading_id,
            latest_stmt.c.robot_id,
            latest_stmt.c.sensor_id,
            latest_stmt.c.sensor_type,
            latest_stmt.c.value,
            latest_stmt.c.recorded_at,
        )
        .order_by(latest_stmt.c.sensor_id)
    )
    if robot_id is not None:
        statement = statement.where(latest_stmt.c.robot_id == robot_id)

    results = []
    for row in db.execute(statement):
        sample_count = int(row.sample_count or 0)
        mean = float(row.mean) if row.mean is not None else None
        stddev = float(row.stddev) if row.stddev is not None else None
        score = score_observation(
            value=float(row.value),
            mean=mean,
            stddev=stddev,
            sample_count=sample_count,
        )
        sensor_type = row.sensor_type.value if hasattr(row.sensor_type, "value") else row.sensor_type
        results.append(
            {
                "reading_id": row.reading_id,
                "robot_id": row.robot_id,
                "sensor_id": row.sensor_id,
                "sensor_type": sensor_type,
                "value": float(row.value),
                "recorded_at": row.recorded_at,
                "baseline_sample_count": sample_count,
                "baseline_mean": mean,
                "baseline_stddev": stddev,
                "z_score": score.z_score,
                "status": score.status,
                "reason": score.reason,
            }
        )

    status_counts = {"normal": 0, "warning": 0, "critical": 0, "insufficient_data": 0}
    for item in results:
        status_counts[item["status"]] += 1

    return {
        "as_of": as_of,
        "window_start": window_start,
        "baseline_hours": baseline_hours,
        "robot_id": robot_id,
        "status_counts": status_counts,
        "results": results,
    }
