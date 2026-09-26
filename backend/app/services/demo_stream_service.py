"""Persist bounded, clearly synthetic telemetry for the hosted portfolio demo."""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Sensor, SensorReading
from scripts.seed import ROBOT_CODES, deterministic_uuid

SOURCE_PREFIX = "roboops-demo-v1:"
INTERVAL = timedelta(minutes=5)
RETENTION = timedelta(days=7)
STARTUP_HISTORY_BUCKETS = 96  # Twenty-four hours at fifteen-minute spacing.

SENSOR_IDS = {
    deterministic_uuid(f"sensor:{robot_code}:{sensor_type}"): (robot_code, sensor_type)
    for robot_code in ROBOT_CODES
    for sensor_type in ("battery", "temperature")
}


def current_bucket(now: datetime) -> datetime:
    now = now.astimezone(timezone.utc)
    return now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)


def synthetic_value(robot_code: str, sensor_type: str, at: datetime) -> float:
    """A reproducible scenario, never a measurement from a physical robot."""
    robot_number = int(robot_code[-3:])
    slot = int(at.timestamp()) // 300
    if sensor_type == "battery":
        return round(72 + robot_number + 2.5 * math.sin((slot + robot_number) / 9), 2)
    if robot_code == "RBT-003" and slot % 12 == 0:
        return 48.0  # Labeled synthetic high-temperature scenario.
    return round(32 + robot_number / 2 + 1.8 * math.sin((slot + robot_number) / 7), 2)


def write_demo_readings(db: Session, *, now: datetime | None = None, startup: bool = False) -> int:
    bucket = current_bucket(now or datetime.now(timezone.utc))
    sensors = db.scalars(select(Sensor).where(Sensor.id.in_(SENSOR_IDS))).all()
    rows = []
    for sensor in sensors:
        robot_code, sensor_type = SENSOR_IDS[sensor.id]
        # At startup backfill a sparse 24-hour chart; later ticks add current readings.
        offsets = range(0, STARTUP_HISTORY_BUCKETS * 3, 3) if startup else (0,)
        for offset in offsets:
            timestamp = bucket - offset * INTERVAL
            event_id = f"{SOURCE_PREFIX}{sensor.sensor_code}:{int(timestamp.timestamp())}"
            rows.append({
                "id": uuid.uuid5(uuid.NAMESPACE_URL, event_id),
                "sensor_id": sensor.id,
                "robot_id": sensor.robot_id,
                "recorded_at": timestamp,
                "value": synthetic_value(robot_code, sensor_type, timestamp),
                "source_event_id": event_id,
            })

    if rows:
        db.execute(insert(SensorReading).values(rows).on_conflict_do_nothing())
        # Only our tagged readings on exact seed sensor IDs are eligible for pruning.
        if bucket.minute == 0:
            db.execute(delete(SensorReading).where(
                SensorReading.sensor_id.in_(SENSOR_IDS),
                SensorReading.source_event_id.like(f"{SOURCE_PREFIX}%"),
                SensorReading.recorded_at < bucket - RETENTION,
            ))
        db.commit()
    return len(rows)


def refresh_demo_readings(*, startup: bool = False) -> int:
    with SessionLocal() as db:
        return write_demo_readings(db, startup=startup)
