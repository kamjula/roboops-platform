from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

confluent_kafka = pytest.importorskip("confluent_kafka")
from confluent_kafka import Consumer, TopicPartition

from app.models import Robot, RobotModel, RobotStatus, Sensor, SensorReading, SensorType, Site
from app.streaming.kafka_consumer import KafkaConsumerConfig, KafkaTelemetryConsumer
from app.streaming.kafka_producer import KafkaTelemetryTransport
from app.streaming.telemetry_events import TelemetryEventEnvelope

pytestmark = pytest.mark.skipif(
    os.environ.get("ROBOOPS_KAFKA_E2E") != "1" or not os.environ.get("KAFKA_BOOTSTRAP_SERVERS"),
    reason="ROBOOPS_KAFKA_E2E=1 and KAFKA_BOOTSTRAP_SERVERS are required",
)

TOPIC = os.environ.get("KAFKA_TELEMETRY_TOPIC", "roboops.telemetry.readings.v1")


class KafkaMessageTimeout(AssertionError):
    pass


class _NonClosingSession:
    def __init__(self, session):
        self.session = session

    def __getattr__(self, name):
        return getattr(self.session, name)

    def close(self):
        pass


def _poll_message(consumer: Consumer, timeout_seconds: float = 15.0):
    deadline = __import__("time").monotonic() + timeout_seconds
    while __import__("time").monotonic() < deadline:
        message = consumer.poll(0.5)
        if message is None:
            continue
        if message.error():
            raise AssertionError(f"Kafka consumer error: {message.error()}")
        return message
    raise KafkaMessageTimeout("timed out waiting for Kafka telemetry event")


def _committed_offset(consumer: Consumer, message) -> int:
    committed = consumer.committed([TopicPartition(message.topic(), message.partition())], timeout=5)[0]
    return committed.offset


def test_real_kafka_event_persists_and_replays_idempotently(db_session):
    site = Site(site_code=f"E2E-{uuid.uuid4().hex[:8]}", name="Kafka E2E Site", timezone="UTC")
    model = RobotModel(
        model_code=f"E2E-MODEL-{uuid.uuid4().hex[:8]}",
        manufacturer="RoboOps",
        name="Kafka E2E Model",
        category="inspection",
    )
    db_session.add_all([site, model])
    db_session.commit()
    robot = Robot(
        robot_code=f"E2E-ROBOT-{uuid.uuid4().hex[:8]}",
        name="Kafka E2E Robot",
        serial_number=f"E2E-SERIAL-{uuid.uuid4().hex[:8]}",
        model_id=model.id,
        site_id=site.id,
        status=RobotStatus.ACTIVE,
        installed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(robot)
    db_session.commit()
    sensor = Sensor(
        robot_id=robot.id,
        sensor_code=f"{robot.robot_code}-TEMP",
        sensor_type=SensorType.TEMPERATURE,
        unit="celsius",
    )
    db_session.add(sensor)
    db_session.commit()

    event = TelemetryEventEnvelope(
        event_version=1,
        event_type="telemetry.reading",
        event_id=f"e2e-event-{uuid.uuid4()}",
        sensor_id=sensor.id,
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        value=42.5,
        source_event_id=f"e2e-source-{uuid.uuid4()}",
        produced_at=datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
    )
    producer = KafkaTelemetryTransport(
        os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        TOPIC,
        "roboops-kafka-e2e-producer",
        delivery_timeout_seconds=10,
    )
    group_id = f"roboops-kafka-e2e-{uuid.uuid4()}"
    consumer = KafkaTelemetryConsumer(
        KafkaConsumerConfig(os.environ["KAFKA_BOOTSTRAP_SERVERS"], topic=TOPIC, group_id=group_id),
        session_factory=lambda: _NonClosingSession(db_session),
    )
    consumer.subscribe()
    try:
        producer.send(event)
        first_message = _poll_message(consumer.consumer)
        consumer.process_message(first_message)
        assert _committed_offset(consumer.consumer, first_message) == first_message.offset() + 1
        first_reading = db_session.query(SensorReading).filter_by(sensor_id=sensor.id, source_event_id=event.source_event_id).one()
        first_id = first_reading.id
        assert first_reading.robot_id == robot.id
        assert first_reading.value == event.value

        producer.send(event)
        replay_message = _poll_message(consumer.consumer)
        consumer.process_message(replay_message)
        assert _committed_offset(consumer.consumer, replay_message) == replay_message.offset() + 1
        readings = db_session.query(SensorReading).filter_by(sensor_id=sensor.id, source_event_id=event.source_event_id).all()
        assert len(readings) == 1
        assert readings[0].id == first_id
        assert readings[0].value == event.value
    finally:
        consumer.close()
        producer.close()