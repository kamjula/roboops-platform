"""Statistical anomaly detection using persisted telemetry history."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    """Score the latest persisted reading per sensor against preceding history."""
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
    )
    if robot_id is not None:
        latest_stmt = latest_stmt.where(SensorReading.robot_id == robot_id)

    results = []
    for latest in db.execute(latest_stmt):
        baseline = db.execute(
            select(
                func.count(SensorReading.id).label("sample_count"),
                func.avg(SensorReading.value).label("mean"),
                func.stddev_samp(SensorReading.value).label("stddev"),
            ).where(
                SensorReading.sensor_id == latest.sensor_id,
                SensorReading.recorded_at >= window_start,
                SensorReading.recorded_at < latest.recorded_at,
            )
        ).one()

        sample_count = int(baseline.sample_count or 0)
        mean = float(baseline.mean) if baseline.mean is not None else None
        stddev = float(baseline.stddev) if baseline.stddev is not None else None
        score = score_observation(
            value=float(latest.value),
            mean=mean,
            stddev=stddev,
            sample_count=sample_count,
        )
        sensor_type = latest.sensor_type.value if hasattr(latest.sensor_type, "value") else latest.sensor_type
        results.append(
            {
                "reading_id": latest.reading_id,
                "robot_id": latest.robot_id,
                "sensor_id": latest.sensor_id,
                "sensor_type": sensor_type,
                "value": float(latest.value),
                "recorded_at": latest.recorded_at,
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
