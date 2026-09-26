"""The opt-in portfolio stream stays repeatable and touches only demo data."""
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import func, select

from app.models import SensorReading
from app.services import demo_stream_service as stream
from scripts.seed import build_robots, build_sensors, seed_reference_data


def test_synthetic_values_are_repeatable_and_bucketed():
    instant = datetime(2026, 9, 26, 12, 7, 30, tzinfo=timezone.utc)
    bucket = stream.current_bucket(instant)
    assert bucket == datetime(2026, 9, 26, 12, 5, tzinfo=timezone.utc)
    assert stream.synthetic_value("RBT-001", "battery", bucket) == stream.synthetic_value(
        "RBT-001", "battery", bucket
    )
    assert stream.synthetic_value("RBT-003", "temperature", bucket.replace(minute=0)) == 48.0


def test_stream_is_idempotent_and_prunes_only_old_tagged_demo_rows(db_session, monkeypatch):
    sites, models, _ = seed_reference_data(db_session)
    build_sensors(db_session, build_robots(db_session, sites, models))
    db_session.commit()
    monkeypatch.setattr(stream, "STARTUP_HISTORY_BUCKETS", 4)
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

    assert stream.write_demo_readings(db_session, now=now, startup=True) == 24 * 4
    assert stream.write_demo_readings(db_session, now=now, startup=True) == 24 * 4
    count = lambda: db_session.scalar(select(func.count()).select_from(SensorReading))
    assert count() == 24 * 4

    sensor_id = next(iter(stream.SENSOR_IDS))
    old = now - stream.RETENTION - timedelta(minutes=5)
    robot_id = db_session.scalars(select(SensorReading.robot_id).where(SensorReading.sensor_id == sensor_id)).first()
    for event_id in (f"{stream.SOURCE_PREFIX}old", "external-old"):
        db_session.add(SensorReading(
            id=uuid.uuid4(), sensor_id=sensor_id, robot_id=robot_id,
            recorded_at=old, value=37.0, source_event_id=event_id,
        ))
    db_session.commit()

    stream.write_demo_readings(db_session, now=now)
    assert count() == 24 * 4 + 1
    assert db_session.scalar(select(SensorReading.id).where(SensorReading.source_event_id == "external-old"))
    assert db_session.scalar(select(SensorReading.id).where(
        SensorReading.source_event_id == f"{stream.SOURCE_PREFIX}old"
    )) is None
