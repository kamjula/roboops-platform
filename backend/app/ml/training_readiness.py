"""Training-readiness gates for predictive-maintenance ML.

RoboOps must not manufacture failure labels. This module validates a labeled
benchmark or future verified production dataset before any supervised model is
trained, and creates chronological train/validation/test partitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class LabeledExample:
    observed_at: datetime
    features: tuple[float, ...]
    label: int


@dataclass(frozen=True)
class TimeSplit:
    train: tuple[LabeledExample, ...]
    validation: tuple[LabeledExample, ...]
    test: tuple[LabeledExample, ...]


class TrainingReadinessError(ValueError):
    """Raised when data cannot support a defensible supervised experiment."""


def chronological_split(
    examples: Sequence[LabeledExample],
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> TimeSplit:
    """Return a leakage-safe chronological split; never shuffle time series."""
    if not 0 < train_fraction < 1:
        raise TrainingReadinessError("train_fraction must be between 0 and 1")
    if not 0 < validation_fraction < 1:
        raise TrainingReadinessError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise TrainingReadinessError("train and validation fractions must leave a test partition")
    if len(examples) < 20:
        raise TrainingReadinessError("at least 20 labeled examples are required")

    ordered = tuple(sorted(examples, key=lambda row: row.observed_at))
    feature_widths = {len(row.features) for row in ordered}
    if len(feature_widths) != 1 or 0 in feature_widths:
        raise TrainingReadinessError("all examples must have the same non-empty feature vector")
    if any(row.label not in (0, 1) for row in ordered):
        raise TrainingReadinessError("binary failure labels must be 0 or 1")
    if {row.label for row in ordered} != {0, 1}:
        raise TrainingReadinessError("dataset must contain both failure and non-failure examples")

    train_end = int(len(ordered) * train_fraction)
    validation_end = train_end + int(len(ordered) * validation_fraction)
    train = ordered[:train_end]
    validation = ordered[train_end:validation_end]
    test = ordered[validation_end:]
    if not train or not validation or not test:
        raise TrainingReadinessError("chronological split produced an empty partition")

    # Each evaluation partition must contain both classes or classification
    # metrics can be misleading/undefined. Training also needs both classes.
    for name, partition in (("train", train), ("validation", validation), ("test", test)):
        if {row.label for row in partition} != {0, 1}:
            raise TrainingReadinessError(f"{name} partition must contain both classes")

    if not (train[-1].observed_at <= validation[0].observed_at <= test[0].observed_at):
        raise TrainingReadinessError("time partitions overlap or are out of order")

    return TimeSplit(train=train, validation=validation, test=test)
