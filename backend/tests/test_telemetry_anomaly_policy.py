from app.services.telemetry_anomaly_policy import (
    AnomalySeverity,
    evaluate_telemetry_anomaly,
)


def test_battery_anomaly_thresholds():
    assert evaluate_telemetry_anomaly("battery", 80).severity == AnomalySeverity.NORMAL
    assert evaluate_telemetry_anomaly("battery", 29).severity == AnomalySeverity.WARNING
    assert evaluate_telemetry_anomaly("battery", 14).severity == AnomalySeverity.CRITICAL
    assert evaluate_telemetry_anomaly("battery", -1).severity == AnomalySeverity.UNKNOWN
    assert evaluate_telemetry_anomaly("battery", 101).severity == AnomalySeverity.UNKNOWN


def test_temperature_anomaly_thresholds():
    assert evaluate_telemetry_anomaly("temperature", 35).severity == AnomalySeverity.NORMAL
    assert evaluate_telemetry_anomaly("temperature", 50).severity == AnomalySeverity.WARNING
    assert evaluate_telemetry_anomaly("temperature", 56).severity == AnomalySeverity.CRITICAL
    assert evaluate_telemetry_anomaly("temperature", 5).severity == AnomalySeverity.UNKNOWN
    assert evaluate_telemetry_anomaly("temperature", 61).severity == AnomalySeverity.UNKNOWN


def test_anomaly_reasons_are_explicit():
    assert evaluate_telemetry_anomaly("battery", 20).reason == "battery_low"
    assert evaluate_telemetry_anomaly("battery", 10).reason == "battery_critical"
    assert evaluate_telemetry_anomaly("temperature", 50).reason == "temperature_high"
    assert evaluate_telemetry_anomaly("temperature", 58).reason == "temperature_critical"


def test_unsupported_sensor_is_unknown():
    result = evaluate_telemetry_anomaly("vibration", 12.5)

    assert result.severity == AnomalySeverity.UNKNOWN
    assert result.reason == "unsupported_sensor_type"
