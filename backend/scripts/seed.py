"""Deterministic, idempotent synthetic seed data for the RoboOps fleet.

Running this script multiple times against the same database produces the
same IDs, timestamps, metric values, and row counts. It intentionally:

- uses uuid.uuid5 (SHA-1 based, a stable process-independent helper) derived
  from a fixed namespace + natural key - never uuid.uuid4
- uses a fixed, timezone-aware REFERENCE_TIME - never datetime.now()/utcnow()
- calls random.seed(SEED) inside run() before any randomised value is
  generated, so pseudo-random jitter is reproducible
- never uses Python's hash() builtin (which is randomised per-process)
- deletes only the exact RBT-001..RBT-012 seed robots before re-inserting,
  never a broad match such as Robot.robot_code.like("RBT-%")

All data below is synthetic and fictional.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import (
    Alert,
    AlertSeverity,
    MaintenanceRecord,
    MaintenanceSchedule,
    MaintenanceStatus,
    Robot,
    RobotModel,
    RobotStatus,
    Sensor,
    SensorReading,
    SensorType,
    Site,
    Technician,
)

# Fixed namespace UUID used to derive every deterministic entity ID via
# uuid.uuid5(SEED_NAMESPACE, name). uuid.uuid4 (random) is never used.
SEED_NAMESPACE = uuid.UUID("a3f1b2c4-5d6e-4f70-8a9b-1c2d3e4f5061")

# Fixed, timezone-aware reference timestamp. datetime.now()/utcnow() are
# intentionally never used so that generated timestamps are reproducible.
REFERENCE_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Fixed seed applied to Python's random module inside run(), before any
# randomised jitter value is generated.
SEED = 20260101

ROBOT_CODES = [f"RBT-{i:03d}" for i in range(1, 13)]


def deterministic_uuid(name: str) -> uuid.UUID:
    """Derive a stable UUID from a natural key using uuid5 (never uuid4)."""
    return uuid.uuid5(SEED_NAMESPACE, name)


SITES = [
    {"site_code": "SITE-HQ", "name": "Headquarters Depot", "address": "1 Fleet Way", "timezone": "UTC"},
    {"site_code": "SITE-WH", "name": "Westside Warehouse", "address": "22 Industrial Rd", "timezone": "UTC"},
]

ROBOT_MODELS = [
    {"model_code": "MODEL-SCOUT", "manufacturer": "RoboOps Robotics", "name": "Scout Mk1", "category": "inspection"},
    {"model_code": "MODEL-HAULER", "manufacturer": "RoboOps Robotics", "name": "Hauler Mk2", "category": "logistics"},
    {
        "model_code": "MODEL-INSPECTOR",
        "manufacturer": "RoboOps Robotics",
        "name": "Inspector Mk1",
        "category": "inspection",
    },
]

TECHNICIANS = [
    {"technician_code": "TECH-001", "name": "Ava Chen", "email": "ava.chen@roboops.example", "phone": "555-0101"},
    {"technician_code": "TECH-002", "name": "Marcus Diaz", "email": "marcus.diaz@roboops.example", "phone": "555-0102"},
    {"technician_code": "TECH-003", "name": "Priya Nair", "email": "priya.nair@roboops.example", "phone": "555-0103"},
    {"technician_code": "TECH-004", "name": "Owen Reid", "email": "owen.reid@roboops.example", "phone": "555-0104"},
]

ROBOT_STATUSES = [
    RobotStatus.ACTIVE,
    RobotStatus.ACTIVE,
    RobotStatus.ACTIVE,
    RobotStatus.IDLE,
    RobotStatus.MAINTENANCE,
    RobotStatus.OFFLINE,
]

SENSOR_SPECS = [
    ("battery", SensorType.BATTERY, "percent"),
    ("temperature", SensorType.TEMPERATURE, "celsius"),
]


def _get_or_create(session, model, code_field: str, code_value: str, name_prefix: str, defaults: dict):
    existing = session.query(model).filter(getattr(model, code_field) == code_value).one_or_none()
    if existing is not None:
        return existing
    obj = model(id=deterministic_uuid(f"{name_prefix}:{code_value}"), **defaults)
    session.add(obj)
    session.flush()
    return obj


def seed_reference_data(session):
    sites = [_get_or_create(session, Site, "site_code", s["site_code"], "site", s) for s in SITES]
    models = [
        _get_or_create(session, RobotModel, "model_code", m["model_code"], "robot_model", m) for m in ROBOT_MODELS
    ]
    technicians = [
        _get_or_create(session, Technician, "technician_code", t["technician_code"], "technician", t)
        for t in TECHNICIANS
    ]
    return sites, models, technicians


def delete_existing_seed_robots(session) -> None:
    """Idempotency: remove only the exact RBT-001..RBT-012 seed robots.

    Deliberately does NOT use a broad match such as
    Robot.robot_code.like("RBT-%"), per project safety rules. Related
    sensors/readings/schedules/records/alerts are removed via the ORM
    cascade defined on Robot's relationships.
    """
    existing = session.query(Robot).filter(Robot.robot_code.in_(ROBOT_CODES)).all()
    for robot in existing:
        session.delete(robot)
    session.flush()


def build_robots(session, sites, models):
    robots = []
    for index, code in enumerate(ROBOT_CODES):
        site = sites[index % len(sites)]
        model = models[index % len(models)]
        status = ROBOT_STATUSES[index % len(ROBOT_STATUSES)]
        robot = Robot(
            id=deterministic_uuid(f"robot:{code}"),
            robot_code=code,
            name=f"Robot {code[-3:]}",
            serial_number=f"SN-{code}-{1000 + index}",
            model_id=model.id,
            site_id=site.id,
            status=status,
            installed_at=REFERENCE_TIME - timedelta(days=30 * (index + 1)),
        )
        session.add(robot)
        robots.append(robot)
    session.flush()
    return robots


def build_sensors(session, robots):
    sensors = []
    for robot in robots:
        for suffix, sensor_type, unit in SENSOR_SPECS:
            sensor = Sensor(
                id=deterministic_uuid(f"sensor:{robot.robot_code}:{suffix}"),
                robot_id=robot.id,
                sensor_code=f"{robot.robot_code}-{suffix.upper()}",
                sensor_type=sensor_type,
                unit=unit,
            )
            session.add(sensor)
            sensors.append(sensor)
    session.flush()
    return sensors


def build_sensor_readings(session, sensors):
    readings = []
    for sensor in sensors:
        base_value = 80.0 if sensor.sensor_type == SensorType.BATTERY else 35.0
        for reading_index in range(5):
            jitter = random.uniform(-2.5, 2.5)
            reading = SensorReading(
                id=deterministic_uuid(f"reading:{sensor.sensor_code}:{reading_index}"),
                sensor_id=sensor.id,
                robot_id=sensor.robot_id,
                recorded_at=REFERENCE_TIME - timedelta(hours=reading_index),
                value=round(base_value + jitter, 2),
            )
            session.add(reading)
            readings.append(reading)
    session.flush()
    return readings


def build_maintenance_schedules(session, robots):
    schedules = []
    for index, robot in enumerate(robots):
        schedule = MaintenanceSchedule(
            id=deterministic_uuid(f"schedule:{robot.robot_code}"),
            robot_id=robot.id,
            scheduled_for=REFERENCE_TIME + timedelta(days=14 + index),
            maintenance_type="routine_inspection",
            status=MaintenanceStatus.SCHEDULED,
            notes=f"Routine inspection for {robot.robot_code}",
        )
        session.add(schedule)
        schedules.append(schedule)
    session.flush()
    return schedules


def build_maintenance_records(session, robots, technicians, schedules):
    records = []
    for index, robot in enumerate(robots):
        technician = technicians[index % len(technicians)]
        schedule = schedules[index]
        record = MaintenanceRecord(
            id=deterministic_uuid(f"record:{robot.robot_code}"),
            robot_id=robot.id,
            technician_id=technician.id,
            schedule_id=schedule.id,
            performed_at=REFERENCE_TIME - timedelta(days=7 * (index + 1)),
            maintenance_type="routine_inspection",
            description=f"Completed routine inspection for {robot.robot_code}",
            cost_usd=round(50.0 + 5.0 * index, 2),
        )
        session.add(record)
        records.append(record)
    session.flush()
    return records


def build_alerts(session, robots, sensors):
    alerts = []
    sensors_by_robot: dict = {}
    for sensor in sensors:
        sensors_by_robot.setdefault(sensor.robot_id, []).append(sensor)

    for index, robot in enumerate(robots):
        if index % 2 != 0:
            continue
        robot_sensors = sensors_by_robot.get(robot.id, [])
        sensor = robot_sensors[0] if robot_sensors else None
        alert = Alert(
            id=deterministic_uuid(f"alert:{robot.robot_code}"),
            robot_id=robot.id,
            sensor_id=sensor.id if sensor else None,
            severity=AlertSeverity.WARNING,
            alert_type="battery_degradation",
            message=f"Battery degradation trend detected for {robot.robot_code}",
            triggered_at=REFERENCE_TIME - timedelta(hours=3),
        )
        session.add(alert)
        alerts.append(alert)
    session.flush()
    return alerts


def run() -> dict:
    """Seed the database deterministically and idempotently.

    Safe to call repeatedly: re-running produces the same IDs, timestamps,
    metric values, and row counts for the RBT-001..RBT-012 fleet.
    """
    random.seed(SEED)

    session = SessionLocal()
    try:
        delete_existing_seed_robots(session)

        sites, models, technicians = seed_reference_data(session)
        robots = build_robots(session, sites, models)
        sensors = build_sensors(session, robots)
        readings = build_sensor_readings(session, sensors)
        schedules = build_maintenance_schedules(session, robots)
        records = build_maintenance_records(session, robots, technicians, schedules)
        alerts = build_alerts(session, robots, sensors)

        session.commit()

        return {
            "sites": len(sites),
            "robot_models": len(models),
            "technicians": len(technicians),
            "robots": len(robots),
            "sensors": len(sensors),
            "sensor_readings": len(readings),
            "maintenance_schedules": len(schedules),
            "maintenance_records": len(records),
            "alerts": len(alerts),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    result = run()
    total = sum(result.values())
    print("RoboOps deterministic seed complete:")
    for table, count in result.items():
        print(f"  {table}: {count}")
    print(f"  total: {total}")
