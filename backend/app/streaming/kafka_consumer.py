"""At-least-once Kafka consumer for telemetry persistence."""
from __future__ import annotations

import json
import logging
import signal
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import ValidationError

from app.schemas.telemetry import TelemetryReadingCreate
from app.services import telemetry_service
from app.streaming.telemetry_events import TelemetryEventEnvelope

LOGGER = logging.getLogger("roboops.kafka_consumer")
DEFAULT_TOPIC = "roboops.telemetry.readings.v1"
DEFAULT_GROUP_ID = "roboops-telemetry-persistence"
DEFAULT_POLL_TIMEOUT_SECONDS = 1.0


class PermanentTelemetryEventError(ValueError):
    """Raised for malformed or permanently invalid Kafka messages."""


class TransientTelemetryPersistenceError(RuntimeError):
    """Raised when persistence fails and the offset must remain uncommitted."""


@dataclass(frozen=True)
class KafkaConsumerConfig:
    bootstrap_servers: str
    topic: str = DEFAULT_TOPIC
    group_id: str = DEFAULT_GROUP_ID
    poll_timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS
    client_id: str = "roboops-telemetry-consumer"

    def __post_init__(self) -> None:
        if not self.bootstrap_servers.strip():
            raise ValueError("bootstrap servers are required")
        if not self.topic.strip() or not self.group_id.strip() or self.poll_timeout_seconds <= 0:
            raise ValueError("topic, group ID, and positive poll timeout are required")


def envelope_to_reading(envelope: TelemetryEventEnvelope) -> TelemetryReadingCreate:
    """Map the authoritative event fields into the existing service input."""
    return TelemetryReadingCreate(
        sensor_id=envelope.sensor_id,
        value=envelope.value,
        observed_at=envelope.observed_at,
        source_event_id=envelope.source_event_id,
    )


def parse_message(raw_value: bytes | str) -> TelemetryEventEnvelope:
    try:
        payload = json.loads(raw_value)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PermanentTelemetryEventError("message is not valid JSON") from exc
    try:
        return TelemetryEventEnvelope.model_validate(payload)
    except ValidationError as exc:
        raise PermanentTelemetryEventError("message failed telemetry envelope validation") from exc


class KafkaTelemetryConsumer:
    """Processes one message at a time and commits only after persistence."""

    def __init__(
        self,
        config: KafkaConsumerConfig,
        *,
        consumer: Any | None = None,
        consumer_factory: Callable[[dict[str, Any]], Any] | None = None,
        session_factory: Callable[[], Any] | None = None,
        ingest: Callable[[Any, TelemetryReadingCreate], Any] = telemetry_service.ingest_reading,
    ):
        self.config = config
        if consumer is not None:
            self.consumer = consumer
        else:
            if consumer_factory is None:
                try:
                    from confluent_kafka import Consumer
                except ImportError as exc:
                    raise RuntimeError("confluent-kafka is required for Kafka consumer") from exc
                consumer_factory = Consumer
            self.consumer = consumer_factory(
                {
                    "bootstrap.servers": config.bootstrap_servers,
                    "group.id": config.group_id,
                    "client.id": config.client_id,
                    "enable.auto.commit": False,
                    "enable.auto.offset.store": False,
                    "auto.offset.reset": "earliest",
                }
            )
        if session_factory is None:
            from app.database import SessionLocal

            session_factory = SessionLocal
        self.session_factory = session_factory
        self.ingest = ingest
        self.running = True

    def subscribe(self) -> None:
        self.consumer.subscribe([self.config.topic])

    def stop(self, *_args: Any) -> None:
        self.running = False

    def close(self) -> None:
        self.consumer.close()

    def process_message(self, message: Any) -> None:
        metadata = (message.topic(), message.partition(), message.offset())
        try:
            envelope = parse_message(message.value())
        except PermanentTelemetryEventError:
            LOGGER.exception("invalid telemetry message topic=%s partition=%s offset=%s", *metadata)
            raise

        LOGGER.info(
            "processing telemetry topic=%s partition=%s offset=%s event_id=%s source_event_id=%s",
            *metadata,
            envelope.event_id,
            envelope.source_event_id,
        )
        session = self.session_factory()
        try:
            self.ingest(session, envelope_to_reading(envelope))
        except Exception as exc:
            session.rollback()
            LOGGER.exception(
                "telemetry persistence failed; offset not committed topic=%s partition=%s offset=%s event_id=%s source_event_id=%s",
                *metadata,
                envelope.event_id,
                envelope.source_event_id,
            )
            raise TransientTelemetryPersistenceError("telemetry persistence failed") from exc
        finally:
            session.close()
        self.consumer.commit(message=message, asynchronous=False)
        LOGGER.info(
            "telemetry offset committed topic=%s partition=%s offset=%s event_id=%s source_event_id=%s",
            *metadata,
            envelope.event_id,
            envelope.source_event_id,
        )

    def run(self) -> None:
        self.subscribe()
        try:
            while self.running:
                message = self.consumer.poll(self.config.poll_timeout_seconds)
                if message is None:
                    continue
                if message.error():
                    LOGGER.error("Kafka consumer error: %s", message.error())
                    continue
                self.process_message(message)
        finally:
            self.close()


def install_signal_handlers(consumer: KafkaTelemetryConsumer) -> None:
    signal.signal(signal.SIGINT, consumer.stop)
    signal.signal(signal.SIGTERM, consumer.stop)
