"""Deterministic telemetry anomaly detection rules."""

from dataclasses import dataclass
from enum import Enum


class AnomalySeverity(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AnomalyResult:
    severity: AnomalySeverity
    reason: str | None


def evaluate_telemetry_anomaly(sensor_type: str, value: float) -> AnomalyResult:
    """
    Evaluate one telemetry reading using explicit deterministic rules.

    This is intentionally rule-based. It provides a transparent baseline
    before introducing statistical or ML-based anomaly detection.
    """

    if sensor_type == "battery":
        if value < 0 or value > 100:
            return AnomalyResult(AnomalySeverity.UNKNOWN, "battery_invalid")
        if value < 15:
            return AnomalyResult(AnomalySeverity.CRITICAL, "battery_critical")
        if value < 30:
            return AnomalyResult(AnomalySeverity.WARNING, "battery_low")
        return AnomalyResult(AnomalySeverity.NORMAL, None)

    if sensor_type == "temperature":
        if value < 10 or value > 60:
            return AnomalyResult(AnomalySeverity.UNKNOWN, "temperature_invalid")
        if value > 55:
            return AnomalyResult(AnomalySeverity.CRITICAL, "temperature_critical")
        if value > 45:
            return AnomalyResult(AnomalySeverity.WARNING, "temperature_high")
        return AnomalyResult(AnomalySeverity.NORMAL, None)

    return AnomalyResult(
        AnomalySeverity.UNKNOWN,
        "unsupported_sensor_type",
    )
