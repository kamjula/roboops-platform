"""Unsupervised condition scoring for real telemetry feature rows.

This module deliberately does not predict failures or remaining useful life.
It learns a baseline from persisted telemetry-derived feature rows and reports
how unusual a row is relative to that baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import fmean, stdev
from typing import Mapping, Sequence

FEATURE_NAMES = (
    "battery_mean",
    "battery_stddev",
    "temperature_mean",
    "temperature_stddev",
)
MIN_BASELINE_ROWS = 20
WARNING_SCORE = 2.0
CRITICAL_SCORE = 3.0


@dataclass(frozen=True)
class FeatureBaseline:
    means: dict[str, float]
    stddevs: dict[str, float]
    row_count: int


@dataclass(frozen=True)
class ConditionScore:
    status: str
    score: float | None
    reason: str
    feature_z_scores: dict[str, float]


def fit_feature_baseline(rows: Sequence[Mapping[str, object]]) -> FeatureBaseline:
    """Fit mean/sample-standard-deviation statistics from complete real rows."""
    if len(rows) < MIN_BASELINE_ROWS:
        raise ValueError("minimum_baseline_rows_not_met")

    means: dict[str, float] = {}
    stddevs: dict[str, float] = {}
    for feature in FEATURE_NAMES:
        values = [row.get(feature) for row in rows]
        if any(value is None or isinstance(value, bool) for value in values):
            raise ValueError("incomplete_required_features")
        numeric = [float(value) for value in values]
        means[feature] = fmean(numeric)
        stddevs[feature] = stdev(numeric)

    return FeatureBaseline(means=means, stddevs=stddevs, row_count=len(rows))


def score_condition(row: Mapping[str, object], baseline: FeatureBaseline) -> ConditionScore:
    """Return RMS absolute z-score across usable features.

    Zero-variance features are omitted rather than assigned fabricated signal.
    If no feature has usable variance, the condition is unknown.
    """
    z_scores: dict[str, float] = {}
    for feature in FEATURE_NAMES:
        value = row.get(feature)
        if value is None or isinstance(value, bool):
            return ConditionScore("unknown", None, "incomplete_required_features", {})
        sigma = baseline.stddevs[feature]
        if sigma > 0:
            z_scores[feature] = (float(value) - baseline.means[feature]) / sigma

    if not z_scores:
        return ConditionScore("unknown", None, "baseline_variance_unavailable", {})

    score = sqrt(sum(z * z for z in z_scores.values()) / len(z_scores))
    if score >= CRITICAL_SCORE:
        status, reason = "critical", "condition_score_at_least_3"
    elif score >= WARNING_SCORE:
        status, reason = "warning", "condition_score_at_least_2"
    else:
        status, reason = "normal", "condition_score_below_2"

    return ConditionScore(status, score, reason, z_scores)
