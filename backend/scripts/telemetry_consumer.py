"""Standalone Kafka telemetry persistence consumer."""
from __future__ import annotations

import os

from app.streaming.kafka_consumer import KafkaConsumerConfig, KafkaTelemetryConsumer, install_signal_handlers


def main() -> int:
    config = KafkaConsumerConfig(
        bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        topic=os.environ.get("KAFKA_TELEMETRY_TOPIC", "roboops.telemetry.readings.v1"),
        group_id=os.environ.get("KAFKA_CONSUMER_GROUP", "roboops-telemetry-persistence"),
        poll_timeout_seconds=float(os.environ.get("KAFKA_POLL_TIMEOUT_SECONDS", "1.0")),
        client_id=os.environ.get("KAFKA_CONSUMER_CLIENT_ID", "roboops-telemetry-consumer"),
    )
    consumer = KafkaTelemetryConsumer(config)
    install_signal_handlers(consumer)
    consumer.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())