"""Truthful readiness checks before supervised predictive-maintenance training."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

REQUIRED_FEATURES = (
    "battery_mean",
    "battery_stddev",
    "temperature_mean",
    "temperature_stddev",
)
MIN_ROWS = 100
MIN_POSITIVE_LABELS = 20
MIN_NEGATIVE_LABELS = 20


@dataclass(frozen=True)
class TrainingReadiness:
    ready: bool
    reasons: tuple[str, ...]
    row_count: int
    labeled_row_count: int
    positive_labels: int
    negative_labels: int


def assess_supervised_training_readiness(
    rows: Sequence[Mapping[str, object]] | Iterable[Mapping[str, object]],
    *,
    label_key: str = "failure_within_horizon",
) -> TrainingReadiness:
    """Decide whether a dataset may enter supervised model evaluation.

    This gate deliberately refuses to infer labels from telemetry thresholds or
    maintenance activity. A row is supervised-training eligible only when an
    explicit boolean failure outcome is present.
    """
    materialized = list(rows)
    reasons: list[str] = []

    if len(materialized) < MIN_ROWS:
        reasons.append("insufficient_feature_rows")

    missing_features = any(
        any(row.get(feature) is None for feature in REQUIRED_FEATURES)
        for row in materialized
    )
    if missing_features:
        reasons.append("incomplete_required_features")

    labels = [row.get(label_key) for row in materialized]
    explicit_labels = [label for label in labels if isinstance(label, bool)]
    if len(explicit_labels) != len(materialized):
        reasons.append("explicit_failure_labels_required")

    positive = sum(label is True for label in explicit_labels)
    negative = sum(label is False for label in explicit_labels)
    if positive < MIN_POSITIVE_LABELS:
        reasons.append("insufficient_positive_labels")
    if negative < MIN_NEGATIVE_LABELS:
        reasons.append("insufficient_negative_labels")

    return TrainingReadiness(
        ready=not reasons,
        reasons=tuple(reasons),
        row_count=len(materialized),
        labeled_row_count=len(explicit_labels),
        positive_labels=positive,
        negative_labels=negative,
    )
