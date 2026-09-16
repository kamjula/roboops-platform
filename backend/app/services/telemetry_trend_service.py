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


def _allocate_point_limits(summary_rows) -> dict[uuid.UUID, int]:
    """Allocate the global point budget fairly across non-empty sensor series."""
    if not summary_rows:
        return {}

    ordered = [(row.sensor_id, int(row.reading_count)) for row in summary_rows]
    allocations = {sensor_id: 0 for sensor_id, _ in ordered}
    remaining = MAX_TREND_POINTS
    active = [(sensor_id, count) for sensor_id, count in ordered if count > 0]

    while remaining > 0 and active:
        share = max(1, remaining // len(active))
        next_active = []
        for sensor_id, count in active:
            needed = count - allocations[sensor_id]
            grant = min(share, needed, remaining)
            allocations[sensor_id] += grant
            remaining -= grant
            if allocations[sensor_id] < count:
                next_active.append((sensor_id, count))
            if remaining == 0:
                break
        active = next_active

    return allocations


def get_telemetry_trends(
    db: Session,
    *,
    as_of: datetime | None = None,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    robot_id: uuid.UUID | None = None,
) -> dict:
    """Return truthful per-sensor summaries plus bounded recent trend points.

    Summary statistics cover the complete requested window. PostgreSQL ranks
    raw readings per sensor in one set-based query; application-side fair-share
    limits then keep the response globally bounded without N+1 point queries.
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

    point_limits = _allocate_point_limits(summary_rows)
    points_by_sensor: dict[uuid.UUID, list[dict]] = {}
    returned_point_count = 0

    if point_limits:
        ranked_points = (
            select(
                SensorReading.sensor_id.label("sensor_id"),
                SensorReading.value.label("value"),
                SensorReading.recorded_at.label("recorded_at"),
                func.row_number()
                .over(
                    partition_by=SensorReading.sensor_id,
                    order_by=(SensorReading.recorded_at.desc(), SensorReading.id.desc()),
                )
                .label("row_number"),
            )
            .join(Sensor, Sensor.id == SensorReading.sensor_id)
            .where(*filters)
            .subquery("ranked_trend_points")
        )

        # The largest fair allocation is a SQL-side upper bound. Sensors with
        # smaller allocations are trimmed below, preserving the exact global
        # budget while avoiding one query per series.
        max_sensor_limit = max(point_limits.values(), default=0)
        if max_sensor_limit > 0:
            point_rows = db.execute(
                select(
                    ranked_points.c.sensor_id,
                    ranked_points.c.value,
                    ranked_points.c.recorded_at,
                    ranked_points.c.row_number,
                )
                .where(ranked_points.c.row_number <= max_sensor_limit)
                .order_by(
                    ranked_points.c.sensor_id.asc(),
                    ranked_points.c.row_number.desc(),
                )
            ).all()

            for point in point_rows:
                sensor_limit = point_limits.get(point.sensor_id, 0)
                if point.row_number > sensor_limit:
                    continue
                points_by_sensor.setdefault(point.sensor_id, []).append(
                    {"recorded_at": point.recorded_at, "value": point.value}
                )
                returned_point_count += 1

    total_readings = sum(int(row.reading_count) for row in summary_rows)
    points_truncated = total_readings > returned_point_count

    series = []
    for row in summary_rows:
        reading_count = int(row.reading_count)
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
