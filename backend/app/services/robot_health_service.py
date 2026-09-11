"""Set-based robot telemetry health aggregation."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Robot, Sensor, SensorReading
from app.schemas.dashboard import RobotHealthItem, RobotHealthResponse, SensorHealthSnapshot
from app.services.robot_health_policy import FRESHNESS_THRESHOLD_SECONDS, SUPPORTED_SENSOR_TYPES, evaluate_robot_health, evaluate_sensor


def get_robot_health(db: Session, as_of: datetime | None = None) -> RobotHealthResponse:
    as_of = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    robots = db.execute(select(Robot).order_by(Robot.robot_code.asc(), Robot.id.asc())).scalars().all()
    ranked = (
        select(
            SensorReading.id.label("reading_id"),
            Sensor.id.label("sensor_id"),
            Sensor.robot_id,
            Sensor.sensor_type,
            Sensor.unit,
            SensorReading.value,
            SensorReading.recorded_at,
            func.row_number().over(
                partition_by=Sensor.id,
                order_by=(SensorReading.recorded_at.desc(), SensorReading.id.desc()),
            ).label("row_number"),
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(Sensor.sensor_type.in_(SUPPORTED_SENSOR_TYPES))
        .subquery()
    )
    rows = db.execute(select(ranked).where(ranked.c.row_number == 1)).all()

    supported_sensors = db.execute(
        select(Sensor).where(Sensor.sensor_type.in_(SUPPORTED_SENSOR_TYPES))
    ).scalars().all()

    configured_by_robot: dict[object, dict[str, Sensor]] = {}
    for sensor in supported_sensors:
        sensor_type = sensor.sensor_type.value if hasattr(sensor.sensor_type, "value") else sensor.sensor_type
        configured_by_robot.setdefault(sensor.robot_id, {})[sensor_type] = sensor

    by_robot: dict[object, dict[str, SensorHealthSnapshot]] = {}
    for row in rows:
        sensor_type = row.sensor_type.value if hasattr(row.sensor_type, "value") else row.sensor_type
        health = evaluate_sensor(sensor_type, row.value, row.recorded_at, row.unit, as_of)
        by_robot.setdefault(row.robot_id, {})[sensor_type] = SensorHealthSnapshot(
            state=health.state.value,
            value=health.value,
            unit=health.unit,
            observed_at=health.observed_at,
            age_seconds=health.age_seconds,
            freshness=health.freshness.value,
            reason_codes=list(health.reason_codes),
        )

    items = []
    for robot in robots:
        configured_sensors = configured_by_robot.get(robot.id, {})
        sensor_snapshots = by_robot.get(robot.id, {})
        sensor_health = {}

        for sensor_type, sensor in configured_sensors.items():
            snapshot = sensor_snapshots.get(sensor_type)
            if snapshot is None:
                sensor_health[sensor_type] = evaluate_sensor(
                    sensor_type, None, None, sensor.unit, as_of
                )
            else:
                sensor_health[sensor_type] = evaluate_sensor(
                    sensor_type,
                    snapshot.value,
                    snapshot.observed_at,
                    snapshot.unit,
                    as_of,
                )

        state, reasons = evaluate_robot_health(robot.status.value, sensor_health)
        items.append(RobotHealthItem(
            robot_id=robot.id,
            robot_code=robot.robot_code,
            robot_name=robot.name,
            operational_status=robot.status.value,
            health_state=state.value,
            reason_codes=list(reasons),
            battery=sensor_snapshots.get("battery"),
            temperature=sensor_snapshots.get("temperature"),
        ))
    return RobotHealthResponse(as_of=as_of, freshness_threshold_seconds=FRESHNESS_THRESHOLD_SECONDS, robots=items)