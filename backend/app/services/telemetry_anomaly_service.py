"""Historical telemetry anomaly aggregation."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Sensor, SensorReading
from app.services.telemetry_anomaly_policy import (
    AnomalySeverity,
    evaluate_telemetry_anomaly,
)


SUPPORTED_ANOMALY_SENSOR_TYPES = ("battery", "temperature")
DEFAULT_LOOKBACK_HOURS = 24
MAX_ANOMALY_EVENTS = 500
ROW_STREAM_BATCH_SIZE = 1000


def get_anomaly_summary(
    db: Session,
    *,
    as_of: datetime | None = None,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
) -> dict:
    """Aggregate deterministic anomalies across the requested time window."""

    as_of = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    window_start = as_of - timedelta(hours=lookback_hours)

    stmt = (
        select(
            SensorReading.id,
            SensorReading.robot_id,
            SensorReading.sensor_id,
            Sensor.sensor_type,
            SensorReading.value,
            SensorReading.recorded_at,
        )
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(
            Sensor.sensor_type.in_(SUPPORTED_ANOMALY_SENSOR_TYPES),
            SensorReading.recorded_at >= window_start,
            SensorReading.recorded_at <= as_of,
        )
        .order_by(
            SensorReading.recorded_at.desc(),
            SensorReading.id.desc(),
        )
    )

    result_rows = db.execute(
        stmt,
        execution_options={"yield_per": ROW_STREAM_BATCH_SIZE},
    )

    severity_counts = Counter(
        {
            AnomalySeverity.NORMAL.value: 0,
            AnomalySeverity.WARNING.value: 0,
            AnomalySeverity.CRITICAL.value: 0,
            AnomalySeverity.UNKNOWN.value: 0,
        }
    )
    reason_counts: Counter[str] = Counter()
    anomaly_events = []
    anomaly_events_truncated = False
    total_readings = 0

    try:
        for row in result_rows:
            total_readings += 1
            sensor_type = (
                row.sensor_type.value
                if hasattr(row.sensor_type, "value")
                else row.sensor_type
            )

            result = evaluate_telemetry_anomaly(sensor_type, row.value)
            severity_counts[result.severity.value] += 1

            if result.reason is not None:
                reason_counts[result.reason] += 1

            if result.severity in {
                AnomalySeverity.WARNING,
                AnomalySeverity.CRITICAL,
            }:
                if len(anomaly_events) < MAX_ANOMALY_EVENTS:
                    anomaly_events.append(
                        {
                            "reading_id": row.id,
                            "robot_id": row.robot_id,
                            "sensor_id": row.sensor_id,
                            "sensor_type": sensor_type,
                            "value": row.value,
                            "severity": result.severity.value,
                            "reason": result.reason,
                            "recorded_at": row.recorded_at,
                        }
                    )
                else:
                    anomaly_events_truncated = True
    finally:
        result_rows.close()

    return {
        "as_of": as_of,
        "window_start": window_start,
        "lookback_hours": lookback_hours,
        "total_readings": total_readings,
        "severity_counts": dict(severity_counts),
        "reason_counts": dict(sorted(reason_counts.items())),
        "anomaly_events": anomaly_events,
        "anomaly_event_limit": MAX_ANOMALY_EVENTS,
        "anomaly_events_truncated": anomaly_events_truncated,
    }
