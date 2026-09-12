"""Centralized, explainable telemetry health policy."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class HealthState(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class Freshness(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"


FRESHNESS_THRESHOLD_SECONDS = 300
SUPPORTED_SENSOR_TYPES = frozenset({"battery", "temperature"})


@dataclass(frozen=True)
class SensorHealth:
    state: HealthState
    value: float | None
    unit: str | None
    observed_at: datetime | None
    age_seconds: int | None
    freshness: Freshness
    reason_codes: tuple[str, ...]


def _age(observed_at: datetime, as_of: datetime) -> int:
    return max(0, int((as_of - observed_at).total_seconds()))


def evaluate_sensor(sensor_type: str, value: float | None, observed_at: datetime | None, unit: str | None, as_of: datetime, freshness_threshold_seconds: int = FRESHNESS_THRESHOLD_SECONDS) -> SensorHealth:
    if observed_at is None or value is None:
        reason = f"{sensor_type}_missing"
        return SensorHealth(HealthState.UNKNOWN, None, unit, None, None, Freshness.MISSING, (reason,))
    normalized_observed_at = observed_at.astimezone(timezone.utc)
    age_seconds = _age(normalized_observed_at, as_of)
    if age_seconds > freshness_threshold_seconds:
        return SensorHealth(HealthState.UNKNOWN, value, unit, normalized_observed_at, age_seconds, Freshness.STALE, (f"{sensor_type}_stale",))

    if sensor_type == "battery":
        if not 0 <= value <= 100:
            return SensorHealth(HealthState.UNKNOWN, value, unit, normalized_observed_at, age_seconds, Freshness.FRESH, ("battery_invalid",))
        if value < 15:
            state, reason = HealthState.CRITICAL, "battery_critical"
        elif value < 30:
            state, reason = HealthState.WARNING, "battery_low"
        else:
            state, reason = HealthState.HEALTHY, "battery_healthy"
    elif sensor_type == "temperature":
        if value < 10 or value > 60:
            return SensorHealth(HealthState.UNKNOWN, value, unit, normalized_observed_at, age_seconds, Freshness.FRESH, ("temperature_invalid",))
        if value > 55:
            state, reason = HealthState.CRITICAL, "temperature_critical"
        elif value > 45:
            state, reason = HealthState.WARNING, "temperature_high"
        else:
            state, reason = HealthState.HEALTHY, "temperature_healthy"
    else:
        return SensorHealth(HealthState.UNKNOWN, value, unit, normalized_observed_at, age_seconds, Freshness.FRESH, ("unsupported_sensor_type",))
    return SensorHealth(state, value, unit, normalized_observed_at, age_seconds, Freshness.FRESH, (reason,))


def evaluate_robot_health(operational_status: str, sensor_health: dict[str, SensorHealth]) -> tuple[HealthState, tuple[str, ...]]:
    reasons: list[str] = []
    if operational_status == "decommissioned":
        return HealthState.UNKNOWN, ("robot_decommissioned",)
    if operational_status == "offline":
        return HealthState.UNKNOWN, ("robot_offline",)
    if operational_status == "maintenance":
        reasons.append("robot_in_maintenance")
    available = [health for health in sensor_health.values() if health.freshness is Freshness.FRESH]
    if not available:
        reasons.append("telemetry_unavailable")
        return HealthState.UNKNOWN, tuple(sorted(reasons))
    if any(health.state is HealthState.CRITICAL for health in available):
        state = HealthState.CRITICAL
    elif any(health.state is HealthState.WARNING for health in available):
        state = HealthState.WARNING
    elif any(health.state is HealthState.UNKNOWN for health in available):
        state = HealthState.UNKNOWN
    else:
        state = HealthState.HEALTHY
    sensor_reasons = [
        reason
        for health in sensor_health.values()
        if health.state is not HealthState.HEALTHY
        for reason in health.reason_codes
    ]
    return state, tuple(sorted(set(reasons + sensor_reasons)))