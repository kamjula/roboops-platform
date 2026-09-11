"""Kafka producer transport for versioned telemetry events."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Event
from typing import Any, Callable

from app.streaming.telemetry_events import TelemetryEventEnvelope

LOGGER = logging.getLogger("roboops.kafka_producer")


class KafkaDeliveryError(RuntimeError):
    """Raised when Kafka does not acknowledge a telemetry event."""


@dataclass(frozen=True)
class KafkaDeliveryResult:
    status_code: int = 202
    accepted: bool = True
    terminal: bool = False
    disable_sensor: bool = False
    disable_robot: bool = False


class KafkaTelemetryTransport:
    """Synchronous, acknowledged Kafka transport with no HTTP or DB access."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        client_id: str,
        *,
        delivery_timeout_seconds: float = 10.0,
        max_retries: int = 3,
        producer: Any | None = None,
        producer_factory: Callable[[dict[str, Any]], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if delivery_timeout_seconds <= 0 or max_retries < 0:
            raise ValueError("delivery timeout must be positive and retries non-negative")
        self.topic = topic
        self.delivery_timeout_seconds = delivery_timeout_seconds
        self.clock = clock
        config = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": client_id,
            "acks": "all",
            "retries": max_retries,
            "delivery.timeout.ms": int(delivery_timeout_seconds * 1000),
        }
        if producer is not None:
            self.producer = producer
        else:
            if producer_factory is None:
                try:
                    from confluent_kafka import Producer
                except ImportError as exc:
                    raise RuntimeError("confluent-kafka is required for Kafka transport") from exc
                producer_factory = Producer
            self.producer = producer_factory(config)
        self.config = config

    def send(self, event: TelemetryEventEnvelope | Any) -> KafkaDeliveryResult:
        if not isinstance(event, TelemetryEventEnvelope):
            event = event.envelope()
        return self.publish(event.serialize(), str(event.sensor_id), event.event_id, event.source_event_id)

    def publish(self, value: bytes, key: str | None, event_id: str, source_event_id: str | None = None) -> KafkaDeliveryResult:
        delivered = Event()
        failure: list[BaseException] = []

        def on_delivery(error, message) -> None:
            if error is not None:
                failure.append(KafkaDeliveryError(str(error)))
            delivered.set()

        try:
            self.producer.produce(
                self.topic,
                key=key,
                value=value,
                on_delivery=on_delivery,
            )
        except Exception as exc:
            raise KafkaDeliveryError(f"failed to enqueue event {event_id}") from exc

        deadline = self.clock() + self.delivery_timeout_seconds
        while not delivered.is_set() and self.clock() < deadline:
            self.producer.poll(0.1)
        if not delivered.is_set():
            raise KafkaDeliveryError(f"delivery timed out for event {event_id}")
        if failure:
            raise failure[0]
        LOGGER.info(
            "event delivered event_id=%s source_event_id=%s topic=%s",
            event_id,
            source_event_id,
            self.topic,
        )
        return KafkaDeliveryResult()

    def close(self, timeout_seconds: float | None = None) -> None:
        timeout = self.delivery_timeout_seconds if timeout_seconds is None else timeout_seconds
        remaining = self.producer.flush(timeout)
        if remaining:
            raise KafkaDeliveryError(f"{remaining} Kafka events remained during flush")


class KafkaDlqPublisher:
    """Publishes bounded DLQ envelopes using the producer delivery path."""

    def __init__(self, bootstrap_servers: str, topic: str = "roboops.telemetry.readings.dlq.v1", client_id: str = "roboops-telemetry-dlq", **kwargs: Any):
        self.transport = KafkaTelemetryTransport(bootstrap_servers, topic, client_id, **kwargs)

    def publish(self, envelope: Any, key: str | None = None) -> KafkaDeliveryResult:
        return self.transport.publish(envelope.serialize(), key, f"dlq:{envelope.source_topic}:{envelope.source_partition}:{envelope.source_offset}", envelope.original_event_id)

    def close(self, timeout_seconds: float | None = None) -> None:
        self.transport.close(timeout_seconds)