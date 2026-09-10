"""Validated telemetry persistence and query operations."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Robot, RobotStatus, Sensor, SensorReading
from app.schemas.telemetry import TelemetryReadingCreate
from app.services.exceptions import ConflictError, IneligibleResourceError, NotFoundError


@dataclass(frozen=True)
class IngestedReading:
    reading: SensorReading
    created: bool


def _get_sensor_and_robot(db: Session, sensor_id: uuid.UUID) -> tuple[Sensor, Robot]:
    sensor = db.get(Sensor, sensor_id)
    if sensor is None:
        raise NotFoundError(f"Sensor {sensor_id} not found")
    robot = db.get(Robot, sensor.robot_id)
    if robot is None:
        raise NotFoundError(f"Robot {sensor.robot_id} not found")
    if robot.status == RobotStatus.DECOMMISSIONED:
        raise IneligibleResourceError("Cannot ingest telemetry for a decommissioned robot")
    return sensor, robot


def _same_payload(reading: SensorReading, payload: TelemetryReadingCreate) -> bool:
    return reading.value == payload.value and reading.recorded_at == payload.observed_at


def _existing_for_event(db: Session, sensor_id: uuid.UUID, source_event_id: str) -> SensorReading | None:
    return db.execute(
        select(SensorReading).where(
            SensorReading.sensor_id == sensor_id,
            SensorReading.source_event_id == source_event_id,
        )
    ).scalar_one_or_none()


def ingest_reading(db: Session, payload: TelemetryReadingCreate) -> IngestedReading:
    sensor, robot = _get_sensor_and_robot(db, payload.sensor_id)
    existing = _existing_for_event(db, sensor.id, payload.source_event_id)
    if existing is not None:
        if _same_payload(existing, payload):
            return IngestedReading(existing, created=False)
        raise ConflictError("Source event ID was already used with a different payload")

    reading = SensorReading(
        sensor_id=sensor.id,
        robot_id=robot.id,
        recorded_at=payload.observed_at,
        value=payload.value,
        source_event_id=payload.source_event_id,
    )
    db.add(reading)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = _existing_for_event(db, sensor.id, payload.source_event_id)
        if existing is None:
            raise
        if _same_payload(existing, payload):
            return IngestedReading(existing, created=False)
        raise ConflictError("Source event ID was already used with a different payload") from exc
    db.refresh(reading)
    return IngestedReading(reading, created=True)


def get_latest_by_robot(db: Session, robot_id: uuid.UUID) -> list[SensorReading]:
    if db.get(Robot, robot_id) is None:
        raise NotFoundError(f"Robot {robot_id} not found")
    ranked = (
        select(
            SensorReading.id,
            func.row_number()
            .over(
                partition_by=SensorReading.sensor_id,
                order_by=(SensorReading.recorded_at.desc(), SensorReading.id.desc()),
            )
            .label("row_number"),
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(Sensor.robot_id == robot_id)
        .subquery()
    )
    return list(
        db.execute(
            select(SensorReading)
            .join(ranked, ranked.c.id == SensorReading.id)
            .where(ranked.c.row_number == 1)
            .order_by(SensorReading.recorded_at.desc(), SensorReading.id.desc())
        ).scalars().all()
    )


def get_sensor_readings(
    db: Session,
    sensor_id: uuid.UUID,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
) -> list[SensorReading]:
    if db.get(Sensor, sensor_id) is None:
        raise NotFoundError(f"Sensor {sensor_id} not found")
    stmt: Select[tuple[SensorReading]] = select(SensorReading).where(SensorReading.sensor_id == sensor_id)
    if start is not None:
        stmt = stmt.where(SensorReading.recorded_at >= start)
    if end is not None:
        stmt = stmt.where(SensorReading.recorded_at <= end)
    stmt = stmt.order_by(SensorReading.recorded_at.desc(), SensorReading.id.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())