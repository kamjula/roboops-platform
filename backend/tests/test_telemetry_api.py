from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Robot, RobotModel, RobotStatus, Sensor, SensorReading, SensorType, Site, UserRole

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set."
)


@pytest.fixture()
def telemetry_fixture(db_session):
    site = Site(site_code=f"SITE-{uuid.uuid4().hex[:8]}", name="Telemetry Site", timezone="UTC")
    model = RobotModel(
        model_code=f"MODEL-{uuid.uuid4().hex[:8]}",
        manufacturer="Acme",
        name="Telemetry Model",
        category="inspection",
    )
    db_session.add_all([site, model])
    db_session.commit()

    robot = Robot(
        robot_code=f"ROBOT-{uuid.uuid4().hex[:8]}",
        name="Telemetry Robot",
        serial_number=f"SERIAL-{uuid.uuid4().hex[:8]}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    other_robot = Robot(
        robot_code=f"ROBOT-{uuid.uuid4().hex[:8]}",
        name="Other Robot",
        serial_number=f"SERIAL-{uuid.uuid4().hex[:8]}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add_all([robot, other_robot])
    db_session.commit()

    sensor = Sensor(
        robot_id=robot.id,
        sensor_code=f"{robot.robot_code}-TEMP",
        sensor_type=SensorType.TEMPERATURE,
        unit="celsius",
    )
    second_sensor = Sensor(
        robot_id=robot.id,
        sensor_code=f"{robot.robot_code}-BATTERY",
        sensor_type=SensorType.BATTERY,
        unit="percent",
    )
    other_sensor = Sensor(
        robot_id=other_robot.id,
        sensor_code=f"{other_robot.robot_code}-TEMP",
        sensor_type=SensorType.TEMPERATURE,
        unit="celsius",
    )
    db_session.add_all([sensor, second_sensor, other_sensor])
    db_session.commit()
    return robot, sensor, second_sensor, other_robot, other_sensor


def payload(sensor_id, *, value=35.5, observed_at="2025-01-01T00:00:00Z", source_event_id="event-1"):
    return {
        "sensor_id": str(sensor_id),
        "value": value,
        "observed_at": observed_at,
        "source_event_id": source_event_id,
    }


def test_ingestion_authorization(unauthenticated_client, viewer_client, operator_client, admin_client, telemetry_fixture):
    _, sensor, *_ = telemetry_fixture
    body = payload(sensor.id)
    assert unauthenticated_client.post("/api/v1/telemetry/readings", json=body).status_code == 401
    assert viewer_client.post("/api/v1/telemetry/readings", json=body).status_code == 403
    assert operator_client.post("/api/v1/telemetry/readings", json=body).status_code == 201
    assert admin_client.post("/api/v1/telemetry/readings", json={**body, "source_event_id": "event-admin"}).status_code == 201


def test_ingestion_persists_sensor_derived_robot_and_utc(operator_client, telemetry_fixture, db_session):
    robot, sensor, *_ = telemetry_fixture
    response = operator_client.post(
        "/api/v1/telemetry/readings",
        json=payload(sensor.id, observed_at="2025-01-01T01:00:00-05:00"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sensor_id"] == str(sensor.id)
    assert body["robot_id"] == str(robot.id)
    assert body["observed_at"] == "2025-01-01T06:00:00Z"
    assert body["source_event_id"] == "event-1"
    stored = db_session.get(SensorReading, uuid.UUID(body["id"]))
    assert stored.robot_id == sensor.robot_id
    assert stored.recorded_at == datetime(2025, 1, 1, 6, tzinfo=timezone.utc)
    assert stored.created_at is not None


def test_client_robot_id_is_rejected(operator_client, telemetry_fixture):
    _, sensor, *_ = telemetry_fixture
    response = operator_client.post(
        "/api/v1/telemetry/readings",
        json={**payload(sensor.id), "robot_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("status_value", [RobotStatus.ACTIVE, RobotStatus.IDLE, RobotStatus.MAINTENANCE, RobotStatus.OFFLINE])
def test_operational_robot_statuses_allow_ingestion(operator_client, telemetry_fixture, db_session, status_value):
    robot, sensor, *_ = telemetry_fixture
    robot.status = status_value
    db_session.commit()
    response = operator_client.post(
        "/api/v1/telemetry/readings",
        json=payload(sensor.id, source_event_id=f"event-{status_value.value}"),
    )
    assert response.status_code == 201


def test_decommissioned_robot_rejects_ingestion(operator_client, telemetry_fixture, db_session):
    robot, sensor, *_ = telemetry_fixture
    robot.status = RobotStatus.DECOMMISSIONED
    db_session.commit()
    response = operator_client.post("/api/v1/telemetry/readings", json=payload(sensor.id))
    assert response.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"sensor_id": "not-a-uuid", "value": 1, "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "x"},
        {"value": 1, "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "x"},
        {"sensor_id": str(uuid.uuid4()), "value": 1, "observed_at": "2025-01-01T00:00:00Z"},
        {"sensor_id": str(uuid.uuid4()), "value": 1, "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "  "},
        {"sensor_id": str(uuid.uuid4()), "value": 1, "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "x" * 129},
        {"sensor_id": str(uuid.uuid4()), "value": 1, "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "x", "extra": True},
        {"sensor_id": str(uuid.uuid4()), "value": float("nan"), "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "x"},
        {"sensor_id": str(uuid.uuid4()), "value": float("inf"), "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "x"},
        {"sensor_id": str(uuid.uuid4()), "value": float("-inf"), "observed_at": "2025-01-01T00:00:00Z", "source_event_id": "x"},
        {"sensor_id": str(uuid.uuid4()), "value": 1, "observed_at": "not-a-timestamp", "source_event_id": "x"},
        {"sensor_id": str(uuid.uuid4()), "value": 1, "observed_at": "2025-01-01T00:00:00", "source_event_id": "x"},
    ],
)
def test_ingestion_validation(operator_client, body):
    assert operator_client.post("/api/v1/telemetry/readings", json=body).status_code == 422


def test_future_timestamp_is_rejected(operator_client, telemetry_fixture):
    _, sensor, *_ = telemetry_fixture
    future = (datetime.now(timezone.utc) + timedelta(minutes=6)).isoformat()
    response = operator_client.post("/api/v1/telemetry/readings", json=payload(sensor.id, observed_at=future))
    assert response.status_code == 422


def test_unknown_sensor_is_not_found(operator_client):
    response = operator_client.post("/api/v1/telemetry/readings", json=payload(uuid.uuid4()))
    assert response.status_code == 404


def test_idempotent_retry_and_conflict(operator_client, telemetry_fixture, db_session):
    _, sensor, *_ = telemetry_fixture
    first = operator_client.post("/api/v1/telemetry/readings", json=payload(sensor.id))
    retry = operator_client.post("/api/v1/telemetry/readings", json={**payload(sensor.id), "source_event_id": " event-1 "})
    different_value = operator_client.post("/api/v1/telemetry/readings", json=payload(sensor.id, value=99))
    different_time = operator_client.post(
        "/api/v1/telemetry/readings", json=payload(sensor.id, observed_at="2025-01-01T00:01:00Z")
    )
    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert different_value.status_code == 409
    assert different_time.status_code == 409
    assert db_session.query(SensorReading).filter_by(sensor_id=sensor.id).count() == 1


def test_database_uniqueness_constraint(db_session, telemetry_fixture):
    _, sensor, *_ = telemetry_fixture
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    db_session.add_all([
        SensorReading(sensor_id=sensor.id, robot_id=sensor.robot_id, recorded_at=timestamp, value=1, source_event_id="unique"),
        SensorReading(sensor_id=sensor.id, robot_id=sensor.robot_id, recorded_at=timestamp, value=2, source_event_id="unique"),
    ])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_anonymous_telemetry_reads_require_authentication(unauthenticated_client, telemetry_fixture):
    robot, sensor, *_ = telemetry_fixture
    assert unauthenticated_client.get(f"/api/v1/telemetry/robots/{robot.id}/latest").status_code == 401
    assert unauthenticated_client.get(f"/api/v1/telemetry/sensors/{sensor.id}/readings").status_code == 401


@pytest.mark.parametrize("fixture_name", ["viewer_client", "operator_client", "admin_client"])
def test_all_roles_can_read_telemetry(request, telemetry_fixture, fixture_name):
    client = request.getfixturevalue(fixture_name)
    robot, sensor, *_ = telemetry_fixture
    assert client.get(f"/api/v1/telemetry/robots/{robot.id}/latest").status_code == 200
    assert client.get(f"/api/v1/telemetry/sensors/{sensor.id}/readings").status_code == 200


def _add_reading(db_session, sensor, recorded_at, value, event_id):
    reading = SensorReading(
        sensor_id=sensor.id,
        robot_id=sensor.robot_id,
        recorded_at=recorded_at,
        value=value,
        source_event_id=event_id,
    )
    db_session.add(reading)
    db_session.flush()
    return reading


def test_latest_is_per_sensor_and_uses_sensor_ownership(operator_client, telemetry_fixture, db_session):
    robot, sensor, second_sensor, other_robot, other_sensor = telemetry_fixture
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    first = _add_reading(db_session, sensor, timestamp, 1, "latest-1")
    latest = _add_reading(db_session, sensor, timestamp, 2, "latest-2")
    second = _add_reading(db_session, second_sensor, timestamp, 3, "latest-3")
    _add_reading(db_session, other_sensor, timestamp + timedelta(hours=1), 99, "other-1")
    db_session.commit()
    response = operator_client.get(f"/api/v1/telemetry/robots/{robot.id}/latest")
    ids = {item["id"] for item in response.json()}
    assert response.status_code == 200
    assert ids == {str(latest.id), str(second.id)}
    assert str(first.id) not in ids
    assert all(item["robot_id"] == str(robot.id) for item in response.json())
    assert str(other_robot.id) not in {item["robot_id"] for item in response.json()}


def test_latest_robot_not_found_and_empty_result(operator_client, telemetry_fixture):
    robot, *_ = telemetry_fixture
    assert operator_client.get(f"/api/v1/telemetry/robots/{uuid.uuid4()}/latest").status_code == 404
    assert operator_client.get(f"/api/v1/telemetry/robots/{robot.id}/latest").json() == []


def test_sensor_history_filters_orders_and_limits(operator_client, telemetry_fixture, db_session):
    _, sensor, *_ = telemetry_fixture
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(3):
        _add_reading(db_session, sensor, base + timedelta(hours=index), index, f"history-{index}")
    db_session.commit()
    path = f"/api/v1/telemetry/sensors/{sensor.id}/readings"
    response = operator_client.get(path, params={"start": "2025-01-01T01:00:00Z", "end": "2025-01-01T02:00:00Z", "limit": 2})
    assert response.status_code == 200
    assert [item["value"] for item in response.json()] == [2, 1]
    assert operator_client.get(path, params={"limit": 501}).status_code == 422
    assert operator_client.get(path, params={"start": "2025-01-02T00:00:00Z", "end": "2025-01-01T00:00:00Z"}).status_code == 422
    assert operator_client.get(path, params={"start": "2025-01-01T00:00:00"}).status_code == 422


def test_sensor_history_not_found(operator_client):
    assert operator_client.get(f"/api/v1/telemetry/sensors/{uuid.uuid4()}/readings").status_code == 404
