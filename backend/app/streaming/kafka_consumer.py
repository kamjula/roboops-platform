"""At-least-once Kafka consumer for telemetry persistence."""
from __future__ import annotations

import json
import logging
import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import ValidationError

from app.schemas.telemetry import TelemetryReadingCreate
from app.services import telemetry_service
from app.services.exceptions import ConflictError, IneligibleResourceError, NotFoundError
from app.streaming.kafka_producer import KafkaDlqPublisher
from app.streaming.telemetry_events import TelemetryDlqEnvelope, TelemetryEventEnvelope

LOGGER = logging.getLogger("roboops.kafka_consumer")
DEFAULT_TOPIC = "roboops.telemetry.readings.v1"
DEFAULT_GROUP_ID = "roboops-telemetry-persistence"
DEFAULT_POLL_TIMEOUT_SECONDS = 1.0
DEFAULT_DLQ_TOPIC = "roboops.telemetry.readings.dlq.v1"
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 0.25


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
    dlq_topic: str = DEFAULT_DLQ_TOPIC
    retry_count: int = DEFAULT_RETRY_COUNT
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS

    def __post_init__(self) -> None:
        if not self.bootstrap_servers.strip():
            raise ValueError("bootstrap servers are required")
        if not self.topic.strip() or not self.group_id.strip() or not self.dlq_topic.strip() or self.poll_timeout_seconds <= 0:
            raise ValueError("topic, group ID, DLQ topic, and positive poll timeout are required")
        if self.retry_count < 0 or self.retry_backoff_seconds < 0:
            raise ValueError("retry count and backoff must be non-negative")


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
        dlq_publisher: Any | None = None,
        dlq_publisher_factory: Callable[[KafkaConsumerConfig], Any] | None = None,
        sleep: Callable[[float], None] = __import__("time").sleep,
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
        if dlq_publisher is None and dlq_publisher_factory is not None:
            dlq_publisher = dlq_publisher_factory(config)
        self.dlq_publisher = dlq_publisher
        self.sleep = sleep
        self.running = True

    def subscribe(self) -> None:
        self.consumer.subscribe([self.config.topic])

    def stop(self, *_args: Any) -> None:
        self.running = False

    def close(self) -> None:
        self.consumer.close()
        if self.dlq_publisher is not None:
            self.dlq_publisher.close()

    @staticmethod
    def _raw_payload(value: Any) -> Any:
        try:
            decoded = json.loads(value)
            json.dumps(decoded, ensure_ascii=False, separators=(",", ":"))
            return decoded
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
            if isinstance(value, bytes):
                return value[:16_384].decode("utf-8", errors="replace")
            return str(value)[:16_384]

    @staticmethod
    def _message_key(message: Any) -> str | None:
        key = getattr(message, "key", lambda: None)()
        if key is None:
            return None
        if isinstance(key, bytes):
            return key[:512].decode("utf-8", errors="replace")
        return str(key)[:512]

    def _publish_dlq_and_commit(self, message: Any, failure_class: str, reason: str, raw_value: Any, envelope: TelemetryEventEnvelope | None = None) -> None:
        if self.dlq_publisher is None:
            raise RuntimeError("DLQ publisher is required for permanent telemetry failures")
        metadata = (message.topic(), message.partition(), message.offset())
        dlq = TelemetryDlqEnvelope(
            dlq_version=1,
            dlq_event_type="telemetry.reading.dlq",
            failure_class=failure_class,
            failure_reason=reason[:512],
            failed_at=datetime.now(timezone.utc),
            source_topic=metadata[0],
            source_partition=metadata[1],
            source_offset=metadata[2],
            source_key=self._message_key(message),
            original_payload=self._raw_payload(raw_value),
            original_event_id=envelope.event_id if envelope else None,
            original_source_event_id=envelope.source_event_id if envelope else None,
        )
        self.dlq_publisher.publish(dlq, key=self._message_key(message))
        self.consumer.commit(message=message, asynchronous=False)
        LOGGER.warning("permanent telemetry message sent to DLQ and committed topic=%s partition=%s offset=%s failure_class=%s event_id=%s source_event_id=%s", *metadata, failure_class, dlq.original_event_id, dlq.original_source_event_id)

    @staticmethod
    def _domain_failure(exc: Exception) -> tuple[str, str] | None:
        if isinstance(exc, NotFoundError):
            return "unknown_sensor", str(exc)
        if isinstance(exc, IneligibleResourceError):
            return "decommissioned_robot", str(exc)
        if isinstance(exc, ConflictError):
            return "idempotency_conflict", str(exc)
        return None

    def process_message(self, message: Any) -> None:
        metadata = (message.topic(), message.partition(), message.offset())
        raw_value = message.value()
        try:
            envelope = parse_message(raw_value)
        except PermanentTelemetryEventError as exc:
            self._publish_dlq_and_commit(message, "invalid_envelope", str(exc), raw_value)
            return

        LOGGER.info(
            "processing telemetry topic=%s partition=%s offset=%s event_id=%s source_event_id=%s",
            *metadata,
            envelope.event_id,
            envelope.source_event_id,
        )
        try:
            payload = envelope_to_reading(envelope)
        except ValidationError as exc:
            self._publish_dlq_and_commit(message, "invalid_reading", str(exc), raw_value, envelope)
            return

        for attempt in range(self.config.retry_count + 1):
            session = self.session_factory()
            try:
                self.ingest(session, payload)
            except Exception as exc:
                session.rollback()
                permanent = self._domain_failure(exc)
                session.close()
                if permanent is not None:
                    self._publish_dlq_and_commit(message, permanent[0], permanent[1], raw_value, envelope)
                    return
                if attempt >= self.config.retry_count:
                    LOGGER.exception("telemetry persistence retries exhausted; offset not committed topic=%s partition=%s offset=%s event_id=%s source_event_id=%s", *metadata, envelope.event_id, envelope.source_event_id)
                    raise TransientTelemetryPersistenceError("telemetry persistence retries exhausted") from exc
                self.sleep(self.config.retry_backoff_seconds * (attempt + 1))
                continue
            finally:
                if not getattr(session, "closed", False):
                    session.close()
            self.consumer.commit(message=message, asynchronous=False)
            break
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
