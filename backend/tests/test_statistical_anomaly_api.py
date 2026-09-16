from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from app.models import Robot, RobotModel, RobotStatus, Sensor, SensorReading, SensorType, Site
from app.services.statistical_anomaly_policy import MIN_BASELINE_SAMPLES

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)


def test_statistical_anomalies_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/dashboard/statistical-anomalies")
    assert response.status_code == 401


def test_statistical_anomalies_validates_baseline_window(client):
    assert client.get("/api/v1/dashboard/statistical-anomalies?baseline_hours=0").status_code == 422
    assert client.get("/api/v1/dashboard/statistical-anomalies?robot_id=not-a-uuid").status_code == 422


def _fixture(db_session, suffix: str):
    site = Site(site_code=f"SA-{suffix}", name="Statistical Anomaly Site", timezone="UTC")
    model = RobotModel(
        model_code=f"SAM-{suffix}",
        manufacturer="Acme",
        name="Stat Scout",
        category="inspection",
    )
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code=f"SAR-{suffix}",
        name="Stat Robot",
        serial_number=f"SAS-{suffix}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    battery = Sensor(
        robot_id=robot.id,
        sensor_code=f"SA-BAT-{suffix}",
        sensor_type=SensorType.BATTERY,
        unit="percent",
    )
    temperature = Sensor(
        robot_id=robot.id,
        sensor_code=f"SA-TMP-{suffix}",
        sensor_type=SensorType.TEMPERATURE,
        unit="celsius",
    )
    vibration = Sensor(
        robot_id=robot.id,
        sensor_code=f"SA-VIB-{suffix}",
        sensor_type=SensorType.VIBRATION,
        unit="mm/s",
    )
    db_session.add_all([battery, temperature, vibration])
    db_session.commit()
    return robot, battery, temperature, vibration


def _add_varying_baseline(db_session, *, sensor, robot, as_of, suffix, value_base):
    readings = []
    for index in range(MIN_BASELINE_SAMPLES):
        readings.append(
            SensorReading(
                sensor_id=sensor.id,
                robot_id=robot.id,
                recorded_at=as_of - timedelta(minutes=MIN_BASELINE_SAMPLES + 1 - index),
                value=value_base + (index % 3),
                source_event_id=f"{suffix}-{index}",
            )
        )
    db_session.add_all(readings)


def test_statistical_anomalies_real_postgres_path(client, db_session):
    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[:8]
    robot, battery, temperature, vibration = _fixture(db_session, suffix)

    readings = []
    for index in range(MIN_BASELINE_SAMPLES):
        readings.append(
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=MIN_BASELINE_SAMPLES + 1 - index),
                value=49.0 + (index % 3),
                source_event_id=f"sa-b-{suffix}-{index}",
            )
        )
    readings.append(
        SensorReading(
            sensor_id=battery.id,
            robot_id=robot.id,
            recorded_at=now - timedelta(seconds=30),
            value=80.0,
            source_event_id=f"sa-b-current-{suffix}",
        )
    )
    for index in range(MIN_BASELINE_SAMPLES - 1):
        readings.append(
            SensorReading(
                sensor_id=temperature.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(minutes=MIN_BASELINE_SAMPLES - index),
                value=30.0 + (index % 2),
                source_event_id=f"sa-t-{suffix}-{index}",
            )
        )
    readings.extend(
        [
            SensorReading(
                sensor_id=temperature.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(seconds=20),
                value=31.0,
                source_event_id=f"sa-t-current-{suffix}",
            ),
            SensorReading(
                sensor_id=vibration.id,
                robot_id=robot.id,
                recorded_at=now - timedelta(seconds=10),
                value=999.0,
                source_event_id=f"sa-v-{suffix}",
            ),
        ]
    )
    db_session.add_all(readings)
    db_session.commit()

    response = client.get(
        f"/api/v1/dashboard/statistical-anomalies?robot_id={robot.id}&baseline_hours=24"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["robot_id"] == str(robot.id)
    assert body["baseline_hours"] == 24
    assert len(body["results"]) == 2

    by_type = {item["sensor_type"]: item for item in body["results"]}
    assert set(by_type) == {"battery", "temperature"}
    battery_result = by_type["battery"]
    assert battery_result["baseline_sample_count"] == MIN_BASELINE_SAMPLES
    assert battery_result["status"] == "critical"
    assert battery_result["z_score"] > 3.0
    assert battery_result["baseline_mean"] < 51.0

    temperature_result = by_type["temperature"]
    assert temperature_result["baseline_sample_count"] == MIN_BASELINE_SAMPLES - 1
    assert temperature_result["status"] == "insufficient_data"
    assert temperature_result["z_score"] is None


def test_future_reading_does_not_enter_baseline(db_session):
    from app.services.statistical_anomaly_service import get_statistical_anomalies

    as_of = datetime.now(timezone.utc).replace(microsecond=0)
    suffix = uuid.uuid4().hex[:8]
    robot, battery, _, _ = _fixture(db_session, suffix)
    _add_varying_baseline(
        db_session,
        sensor=battery,
        robot=robot,
        as_of=as_of,
        suffix=f"leak-base-{suffix}",
        value_base=49.0,
    )
    db_session.add_all(
        [
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=as_of - timedelta(seconds=5),
                value=80.0,
                source_event_id=f"leak-current-{suffix}",
            ),
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=as_of + timedelta(minutes=1),
                value=-10000.0,
                source_event_id=f"leak-future-{suffix}",
            ),
        ]
    )
    db_session.commit()

    result = get_statistical_anomalies(db_session, as_of=as_of, robot_id=robot.id)
    assert len(result["results"]) == 1
    scored = result["results"][0]
    assert scored["value"] == 80.0
    assert scored["baseline_sample_count"] == MIN_BASELINE_SAMPLES
    assert 49.0 < scored["baseline_mean"] < 51.0
    assert scored["status"] == "critical"


def test_statistical_anomaly_service_uses_one_select_for_multiple_sensors(db_session):
    """Adding supported sensors must not add baseline SELECT round trips."""
    from app.services.statistical_anomaly_service import get_statistical_anomalies

    as_of = datetime.now(timezone.utc).replace(microsecond=0)
    suffix = uuid.uuid4().hex[:8]
    robot, battery, temperature, _ = _fixture(db_session, suffix)

    _add_varying_baseline(
        db_session,
        sensor=battery,
        robot=robot,
        as_of=as_of,
        suffix=f"query-b-{suffix}",
        value_base=49.0,
    )
    _add_varying_baseline(
        db_session,
        sensor=temperature,
        robot=robot,
        as_of=as_of,
        suffix=f"query-t-{suffix}",
        value_base=29.0,
    )
    db_session.add_all(
        [
            SensorReading(
                sensor_id=battery.id,
                robot_id=robot.id,
                recorded_at=as_of - timedelta(seconds=5),
                value=80.0,
                source_event_id=f"query-b-current-{suffix}",
            ),
            SensorReading(
                sensor_id=temperature.id,
                robot_id=robot.id,
                recorded_at=as_of - timedelta(seconds=4),
                value=60.0,
                source_event_id=f"query-t-current-{suffix}",
            ),
        ]
    )
    db_session.commit()

    # SQLAlchemy expires ORM instances on commit. Capture the scalar ID before
    # attaching the listener so a lazy refresh of ``robot.id`` is not counted
    # as a service query.
    robot_id = robot.id
    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", count_selects)
    try:
        result = get_statistical_anomalies(db_session, as_of=as_of, robot_id=robot_id)
    finally:
        event.remove(bind, "before_cursor_execute", count_selects)

    assert len(result["results"]) == 2
    assert select_count == 1
