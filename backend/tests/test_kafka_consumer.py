from __future__ import annotations

import json
import uuid

import pytest

from app.streaming.kafka_consumer import (
    DEFAULT_GROUP_ID,
    DEFAULT_TOPIC,
    KafkaConsumerConfig,
    KafkaTelemetryConsumer,
    PermanentTelemetryEventError,
    TransientTelemetryPersistenceError,
    envelope_to_reading,
    parse_message,
)
from app.streaming.telemetry_events import TelemetryEventEnvelope


class FakeSession:
    def __init__(self):
        self.rollback_calls = 0
        self.close_calls = 0

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.close_calls += 1


class FakeMessage:
    def __init__(self, value):
        self._value = value
        self.committed = False

    def topic(self):
        return "roboops.telemetry.readings.v1"

    def partition(self):
        return 0

    def offset(self):
        return 12

    def value(self):
        return self._value

    def error(self):
        return None


class FakeConsumer:
    def __init__(self):
        self.commits = []
        self.closed = False
        self.subscriptions = []

    def subscribe(self, topics):
        self.subscriptions.append(topics)

    def commit(self, *, message, asynchronous):
        self.commits.append((message, asynchronous))

    def close(self):
        self.closed = True


class FakeDlqPublisher:
    def __init__(self, fail=False):
        self.fail = fail
        self.events = []
        self.closed = False

    def publish(self, envelope, key=None):
        if self.fail:
            raise RuntimeError("DLQ unavailable")
        self.events.append((envelope, key))

    def close(self):
        self.closed = True


def event_payload():
    return TelemetryEventEnvelope(
        event_version=1,
        event_type="telemetry.reading",
        event_id="event-1",
        sensor_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        observed_at="2026-09-10T12:00:00Z",
        value=42.5,
        source_event_id="source-1",
        produced_at="2026-09-10T12:00:01Z",
    ).serialize()


def test_mapping_and_configuration_defaults():
    envelope = parse_message(event_payload())
    reading = envelope_to_reading(envelope)
    assert reading.sensor_id == envelope.sensor_id
    assert reading.value == envelope.value
    assert reading.source_event_id == envelope.source_event_id
    config = KafkaConsumerConfig("localhost:9092")
    assert config.topic == DEFAULT_TOPIC
    assert config.group_id == DEFAULT_GROUP_ID


def test_valid_event_persists_then_commits_offset():
    consumer = FakeConsumer()
    session = FakeSession()
    ingested = []
    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092"),
        consumer=consumer,
        session_factory=lambda: session,
        ingest=lambda db, payload: ingested.append((db, payload)),
    )
    message = FakeMessage(event_payload())
    processor.process_message(message)
    assert len(ingested) == 1
    assert len(consumer.commits) == 1
    assert consumer.commits[0][1] is False
    assert session.close_calls == 1


def test_duplicate_replay_result_is_success_and_commits():
    consumer = FakeConsumer()
    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092"),
        consumer=consumer,
        session_factory=FakeSession,
        ingest=lambda db, payload: type("Result", (), {"created": False})(),
    )
    processor.process_message(FakeMessage(event_payload()))
    assert len(consumer.commits) == 1


def test_validation_failure_does_not_hit_service_or_commit():
    consumer = FakeConsumer()
    dlq = FakeDlqPublisher()
    calls = []
    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092"),
        consumer=consumer,
        ingest=lambda db, payload: calls.append(payload),
        dlq_publisher=dlq,
    )
    processor.process_message(FakeMessage(b"not-json"))
    assert calls == []
    assert len(consumer.commits) == 1
    assert dlq.events[0][0].failure_class == "invalid_envelope"


def test_persistence_failure_rolls_back_and_does_not_commit():
    consumer = FakeConsumer()
    session = FakeSession()

    def fail(db, payload):
        raise RuntimeError("database unavailable")

    processor = KafkaTelemetryConsumer(KafkaConsumerConfig("localhost:9092", retry_count=0), consumer=consumer, session_factory=lambda: session, ingest=fail)
    with pytest.raises(TransientTelemetryPersistenceError):
        processor.process_message(FakeMessage(event_payload()))
    assert session.rollback_calls == 1
    assert consumer.commits == []


def test_close_and_shutdown():
    consumer = FakeConsumer()
    processor = KafkaTelemetryConsumer(KafkaConsumerConfig("localhost:9092"), consumer=consumer)
    processor.stop()
    assert processor.running is False
    processor.close()
    assert consumer.closed is True


def test_domain_failure_goes_to_dlq_and_commits():
    consumer = FakeConsumer()
    dlq = FakeDlqPublisher()
    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092"),
        consumer=consumer,
        session_factory=FakeSession,
        ingest=lambda db, payload: (_ for _ in ()).throw(__import__("app.services.exceptions", fromlist=["NotFoundError"]).NotFoundError("Sensor missing")),
        dlq_publisher=dlq,
    )
    processor.process_message(FakeMessage(event_payload()))
    assert dlq.events[0][0].failure_class == "unknown_sensor"
    assert len(consumer.commits) == 1


def test_dlq_failure_does_not_commit():
    consumer = FakeConsumer()
    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092"),
        consumer=consumer,
        dlq_publisher=FakeDlqPublisher(fail=True),
    )
    with pytest.raises(RuntimeError, match="DLQ unavailable"):
        processor.process_message(FakeMessage(b"not-json"))
    assert consumer.commits == []


def test_transient_failure_retries_and_eventually_commits():
    consumer = FakeConsumer()
    session = FakeSession()
    attempts = []
    sleeps = []

    def ingest(db, payload):
        attempts.append(payload)
        if len(attempts) == 1:
            raise RuntimeError("database unavailable")

    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092", retry_count=2, retry_backoff_seconds=0.1),
        consumer=consumer,
        session_factory=lambda: session,
        ingest=ingest,
        sleep=sleeps.append,
    )
    processor.process_message(FakeMessage(event_payload()))
    assert len(attempts) == 2
    assert sleeps == [0.1]
    assert len(consumer.commits) == 1


def test_transient_failure_exhaustion_does_not_commit():
    consumer = FakeConsumer()
    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092", retry_count=2, retry_backoff_seconds=0),
        consumer=consumer,
        session_factory=FakeSession,
        ingest=lambda db, payload: (_ for _ in ()).throw(RuntimeError("database unavailable")),
        sleep=lambda _: None,
    )
    with pytest.raises(TransientTelemetryPersistenceError):
        processor.process_message(FakeMessage(event_payload()))
    assert consumer.commits == []


def test_consumer_configuration_disables_auto_commit():
    configs = []

    class FactoryConsumer(FakeConsumer):
        pass

    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092"),
        consumer_factory=lambda config: (configs.append(config) or FactoryConsumer()),
    )
    assert processor.consumer is not None
    assert configs[0]["enable.auto.commit"] is False
    assert configs[0]["enable.auto.offset.store"] is False


def test_malformed_json_is_explicit():
    with pytest.raises(PermanentTelemetryEventError):
        parse_message("not-json")
