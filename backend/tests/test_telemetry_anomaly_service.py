from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.telemetry_anomaly_service import (
    MAX_ANOMALY_EVENTS,
    ROW_STREAM_BATCH_SIZE,
    get_anomaly_summary,
)


def _result_for_rows(rows):
    result = MagicMock()
    result.__iter__.return_value = iter(rows)
    return result


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
    result_rows = _result_for_rows(rows)
    db.execute.return_value = result_rows

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
    assert result["anomaly_event_limit"] == MAX_ANOMALY_EVENTS
    assert result["anomaly_events_truncated"] is False
    result_rows.close.assert_called_once_with()


def test_anomaly_summary_empty_window():
    as_of = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)

    db = MagicMock()
    result_rows = _result_for_rows([])
    db.execute.return_value = result_rows

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
    assert result["anomaly_event_limit"] == MAX_ANOMALY_EVENTS
    assert result["anomaly_events_truncated"] is False
    result_rows.close.assert_called_once_with()


def test_anomaly_summary_caps_events_but_not_counts_when_over_limit():
    as_of = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
    total_warning_rows = MAX_ANOMALY_EVENTS + 1

    rows = [
        SimpleNamespace(
            id=f"r{index}",
            robot_id="robot-1",
            sensor_id="sensor-1",
            sensor_type="battery",
            value=20.0,
            recorded_at=as_of - timedelta(seconds=index),
        )
        for index in range(total_warning_rows)
    ]

    db = MagicMock()
    db.execute.return_value = _result_for_rows(rows)

    result = get_anomaly_summary(
        db,
        as_of=as_of,
        lookback_hours=24,
    )

    assert result["total_readings"] == total_warning_rows
    assert result["severity_counts"]["warning"] == total_warning_rows
    assert result["reason_counts"] == {"battery_low": total_warning_rows}
    assert len(result["anomaly_events"]) == MAX_ANOMALY_EVENTS
    assert result["anomaly_event_limit"] == MAX_ANOMALY_EVENTS
    assert result["anomaly_events_truncated"] is True
    assert result["anomaly_events"][0]["reading_id"] == "r0"
    assert result["anomaly_events"][-1]["reading_id"] == f"r{MAX_ANOMALY_EVENTS - 1}"


def test_anomaly_summary_streams_and_closes_result():
    as_of = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
    db = MagicMock()
    result_rows = _result_for_rows([])
    db.execute.return_value = result_rows

    get_anomaly_summary(db, as_of=as_of, lookback_hours=24)

    assert db.execute.call_count == 1
    assert db.execute.call_args.kwargs["execution_options"] == {
        "yield_per": ROW_STREAM_BATCH_SIZE,
    }
    result_rows.close.assert_called_once_with()
