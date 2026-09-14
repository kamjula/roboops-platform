from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.telemetry_anomaly_service import get_anomaly_summary


def test_anomaly_summary_aggregates_expected_counts():
    as_of = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)

    rows = [
        SimpleNamespace(
            id="r1",
            robot_id="robot-1",
            sensor_id="sensor-1",
            sensor_type="battery",
            value=80.0,
            recorded_at=as_of - timedelta(minutes=5),
        ),
        SimpleNamespace(
            id="r2",
            robot_id="robot-1",
            sensor_id="sensor-1",
            sensor_type="battery",
            value=20.0,
            recorded_at=as_of - timedelta(minutes=10),
        ),
        SimpleNamespace(
            id="r3",
            robot_id="robot-2",
            sensor_id="sensor-2",
            sensor_type="temperature",
            value=58.0,
            recorded_at=as_of - timedelta(minutes=15),
        ),
    ]

    db = MagicMock()
    db.execute.return_value.all.return_value = rows

    result = get_anomaly_summary(
        db,
        as_of=as_of,
        lookback_hours=24,
    )

    assert result["total_readings"] == 3
    assert result["severity_counts"]["normal"] == 1
    assert result["severity_counts"]["warning"] == 1
    assert result["severity_counts"]["critical"] == 1
    assert result["severity_counts"]["unknown"] == 0

    assert result["reason_counts"] == {
        "battery_low": 1,
        "temperature_critical": 1,
    }

    assert len(result["anomaly_events"]) == 2
    assert result["anomaly_events"][0]["severity"] == "warning"
    assert result["anomaly_events"][1]["severity"] == "critical"


def test_anomaly_summary_empty_window():
    as_of = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)

    db = MagicMock()
    db.execute.return_value.all.return_value = []

    result = get_anomaly_summary(
        db,
        as_of=as_of,
        lookback_hours=24,
    )

    assert result["total_readings"] == 0
    assert result["severity_counts"] == {
        "normal": 0,
        "warning": 0,
        "critical": 0,
        "unknown": 0,
    }
    assert result["reason_counts"] == {}
    assert result["anomaly_events"] == []
