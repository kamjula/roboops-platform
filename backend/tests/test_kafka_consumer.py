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
    calls = []
    processor = KafkaTelemetryConsumer(
        KafkaConsumerConfig("localhost:9092"),
        consumer=consumer,
        ingest=lambda db, payload: calls.append(payload),
    )
    with pytest.raises(PermanentTelemetryEventError):
        processor.process_message(FakeMessage(b"not-json"))
    assert calls == []
    assert consumer.commits == []


def test_persistence_failure_rolls_back_and_does_not_commit():
    consumer = FakeConsumer()
    session = FakeSession()

    def fail(db, payload):
        raise RuntimeError("database unavailable")

    processor = KafkaTelemetryConsumer(KafkaConsumerConfig("localhost:9092"), consumer=consumer, session_factory=lambda: session, ingest=fail)
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
