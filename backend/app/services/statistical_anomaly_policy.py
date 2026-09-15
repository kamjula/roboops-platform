"""Statistical anomaly scoring policy for telemetry observations."""

from __future__ import annotations

from dataclasses import dataclass

MIN_BASELINE_SAMPLES = 20
WARNING_Z_SCORE = 2.0
CRITICAL_Z_SCORE = 3.0


@dataclass(frozen=True)
class StatisticalScore:
    status: str
    z_score: float | None
    reason: str


def score_observation(*, value: float, mean: float | None, stddev: float | None, sample_count: int) -> StatisticalScore:
    """Score one observation using a baseline computed from preceding readings."""
    if sample_count < MIN_BASELINE_SAMPLES:
        return StatisticalScore("insufficient_data", None, "minimum_baseline_samples_not_met")
    if mean is None or stddev is None or stddev <= 0.0:
        return StatisticalScore("insufficient_data", None, "baseline_variance_unavailable")

    z_score = (value - mean) / stddev
    magnitude = abs(z_score)
    if magnitude >= CRITICAL_Z_SCORE:
        return StatisticalScore("critical", z_score, "absolute_z_score_at_least_3")
    if magnitude >= WARNING_Z_SCORE:
        return StatisticalScore("warning", z_score, "absolute_z_score_at_least_2")
    return StatisticalScore("normal", z_score, "absolute_z_score_below_2")
