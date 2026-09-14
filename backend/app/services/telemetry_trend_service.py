"""Historical telemetry trend analytics for supported robot sensors."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Robot, Sensor, SensorReading


SUPPORTED_TREND_SENSOR_TYPES = ("battery", "temperature")
DEFAULT_LOOKBACK_HOURS = 24
MAX_TREND_POINTS = 1000


def _normalize_as_of(as_of: datetime | None) -> datetime:
    value = as_of or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _sensor_type_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def get_telemetry_trends(
    db: Session,
    *,
    as_of: datetime | None = None,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    robot_id: uuid.UUID | None = None,
) -> dict:
    """Return truthful per-sensor summaries plus bounded recent trend points.

    Summary statistics cover the complete requested window. Returned raw
    trend points are globally capped so the API response remains bounded.
    """

    as_of = _normalize_as_of(as_of)
    window_start = as_of - timedelta(hours=lookback_hours)

    filters = [
        Sensor.sensor_type.in_(SUPPORTED_TREND_SENSOR_TYPES),
        SensorReading.recorded_at >= window_start,
        SensorReading.recorded_at <= as_of,
    ]
    if robot_id is not None:
        filters.append(SensorReading.robot_id == robot_id)

    summary_rows = db.execute(
        select(
            SensorReading.robot_id,
            Robot.robot_code,
            Robot.name.label("robot_name"),
            SensorReading.sensor_id,
            Sensor.sensor_type,
            Sensor.unit,
            func.count(SensorReading.id).label("reading_count"),
            func.min(SensorReading.value).label("min_value"),
            func.max(SensorReading.value).label("max_value"),
            func.avg(SensorReading.value).label("avg_value"),
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .join(Robot, Robot.id == SensorReading.robot_id)
        .where(*filters)
        .group_by(
            SensorReading.robot_id,
            Robot.robot_code,
            Robot.name,
            SensorReading.sensor_id,
            Sensor.sensor_type,
            Sensor.unit,
        )
        .order_by(Robot.robot_code.asc(), Sensor.sensor_type.asc(), SensorReading.sensor_id.asc())
    ).all()

    latest_rows = db.execute(
        select(
            SensorReading.sensor_id,
            SensorReading.value,
            SensorReading.recorded_at,
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(*filters)
        .distinct(SensorReading.sensor_id)
        .order_by(
            SensorReading.sensor_id,
            SensorReading.recorded_at.desc(),
            SensorReading.id.desc(),
        )
    ).all()
    latest_by_sensor = {
        row.sensor_id: (row.value, row.recorded_at)
        for row in latest_rows
    }

    point_rows = db.execute(
        select(
            SensorReading.sensor_id,
            SensorReading.value,
            SensorReading.recorded_at,
            SensorReading.id,
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(*filters)
        .order_by(
            SensorReading.recorded_at.desc(),
            SensorReading.id.desc(),
        )
        .limit(MAX_TREND_POINTS + 1)
    ).all()

    points_truncated = len(point_rows) > MAX_TREND_POINTS
    point_rows = point_rows[:MAX_TREND_POINTS]

    points_by_sensor: dict[uuid.UUID, list[dict]] = {}
    for row in point_rows:
        points_by_sensor.setdefault(row.sensor_id, []).append(
            {
                "recorded_at": row.recorded_at,
                "value": row.value,
            }
        )

    # The query is newest-first for the global cap; each returned series is
    # exposed oldest-first so clients can plot it directly.
    for points in points_by_sensor.values():
        points.reverse()

    series = []
    total_readings = 0
    for row in summary_rows:
        reading_count = int(row.reading_count)
        total_readings += reading_count
        latest_value, latest_recorded_at = latest_by_sensor[row.sensor_id]

        series.append(
            {
                "robot_id": row.robot_id,
                "robot_code": row.robot_code,
                "robot_name": row.robot_name,
                "sensor_id": row.sensor_id,
                "sensor_type": _sensor_type_value(row.sensor_type),
                "unit": row.unit,
                "reading_count": reading_count,
                "min_value": float(row.min_value),
                "max_value": float(row.max_value),
                "avg_value": float(row.avg_value),
                "latest_value": float(latest_value),
                "latest_recorded_at": latest_recorded_at,
                "points": points_by_sensor.get(row.sensor_id, []),
            }
        )

    return {
        "as_of": as_of,
        "window_start": window_start,
        "lookback_hours": lookback_hours,
        "robot_id": robot_id,
        "total_readings": total_readings,
        "series_count": len(series),
        "point_limit": MAX_TREND_POINTS,
        "points_truncated": points_truncated,
        "series": series,
    }
