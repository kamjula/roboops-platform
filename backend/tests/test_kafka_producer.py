from __future__ import annotations

import json
import uuid

import pytest

from app.streaming.kafka_producer import KafkaDeliveryError, KafkaTelemetryTransport
from app.streaming.telemetry_events import TelemetryEventEnvelope


def event():
    return TelemetryEventEnvelope(
        event_version=1,
        event_type="telemetry.reading",
        event_id="event-1",
        sensor_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        observed_at="2026-09-10T12:00:00Z",
        value=42.5,
        source_event_id="source-1",
        produced_at="2026-09-10T12:00:01Z",
    )


class FakeProducer:
    def __init__(self, error=None):
        self.error = error
        self.calls = []
        self.poll_calls = 0
        self.flush_calls = []

    def produce(self, topic, *, key, value, on_delivery):
        self.calls.append((topic, key, value))
        on_delivery(self.error, object())

    def poll(self, timeout):
        self.poll_calls += 1

    def flush(self, timeout):
        self.flush_calls.append(timeout)
        return 0


def test_producer_configures_acknowledged_delivery_and_serialized_key_payload():
    producer = FakeProducer()
    transport = KafkaTelemetryTransport(
        "localhost:9092",
        "roboops.telemetry.readings.v1",
        "test-client",
        producer=producer,
    )
    result = transport.send(event())
    assert result.accepted is True
    assert producer.calls[0][0] == "roboops.telemetry.readings.v1"
    assert producer.calls[0][1] == "11111111-1111-1111-1111-111111111111"
    assert json.loads(producer.calls[0][2])[
        "source_event_id"
    ] == "source-1"
    assert transport.config["acks"] == "all"
    assert transport.config["delivery.timeout.ms"] == 10000


def test_delivery_failure_is_propagated_and_close_flushes():
    producer = FakeProducer(error=RuntimeError("broker rejected message"))
    transport = KafkaTelemetryTransport("localhost:9092", "topic", "client", producer=producer)
    with pytest.raises(KafkaDeliveryError, match="broker rejected"):
        transport.send(event())
    transport.close(2.5)
    assert producer.flush_calls == [2.5]


def test_invalid_retry_configuration_is_rejected():
    with pytest.raises(ValueError):
        KafkaTelemetryTransport("localhost:9092", "topic", "client", delivery_timeout_seconds=0)
    with pytest.raises(ValueError):
        KafkaTelemetryTransport("localhost:9092", "topic", "client", max_retries=-1)