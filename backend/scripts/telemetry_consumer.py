"""Standalone Kafka telemetry persistence consumer."""
from __future__ import annotations

import os

from app.streaming.kafka_consumer import KafkaConsumerConfig, KafkaTelemetryConsumer, install_signal_handlers
from app.streaming.kafka_producer import KafkaDlqPublisher


def main() -> int:
    config = KafkaConsumerConfig(
        bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        topic=os.environ.get("KAFKA_TELEMETRY_TOPIC", "roboops.telemetry.readings.v1"),
        group_id=os.environ.get("KAFKA_CONSUMER_GROUP", "roboops-telemetry-persistence"),
        poll_timeout_seconds=float(os.environ.get("KAFKA_POLL_TIMEOUT_SECONDS", "1.0")),
        client_id=os.environ.get("KAFKA_CONSUMER_CLIENT_ID", "roboops-telemetry-consumer"),
        dlq_topic=os.environ.get("KAFKA_TELEMETRY_DLQ_TOPIC", "roboops.telemetry.readings.dlq.v1"),
        retry_count=int(os.environ.get("KAFKA_RETRY_COUNT", "3")),
        retry_backoff_seconds=float(os.environ.get("KAFKA_RETRY_BACKOFF_SECONDS", "0.25")),
    )
    dlq_publisher = KafkaDlqPublisher(config.bootstrap_servers, config.dlq_topic)
    consumer = KafkaTelemetryConsumer(config, dlq_publisher=dlq_publisher)
    install_signal_handlers(consumer)
    consumer.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
