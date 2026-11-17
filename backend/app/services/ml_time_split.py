"""Time-aware train/validation/test splits for predictive-maintenance features.

Contract:

* Rows are ordered by their timestamp (``bucket_start`` by default). Every
  training timestamp is earlier than every validation timestamp, and every
  validation timestamp is earlier than every test timestamp.
* Cut points fall between distinct timestamps, so rows that share a timestamp
  (for example, several robots in the same hour) always land in the same split.
* An optional ``gap`` purges rows at the start of the validation and test
  splits that sit within ``gap`` of the previous split's last timestamp. Set it
  to at least the label horizon so a training label never looks into the
  validation or test period.
* The same rows always produce the same split, whatever order they arrive in.

Supervised use must go through ``prepare_supervised_splits``, which runs the
training-readiness gate first and refuses unlabeled telemetry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Sequence

from app.services.ml_training_readiness import require_supervised_training_ready

Row = Mapping[str, object]


@dataclass(frozen=True)
class TimeSplit:
    train: tuple[Row, ...]
    validation: tuple[Row, ...]
    test: tuple[Row, ...]
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    test_start: datetime
    gap: timedelta
    purged_row_count: int


def chronological_split(
    rows: Sequence[Row] | Iterable[Row],
    *,
    time_key: str = "bucket_start",
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
    gap: timedelta = timedelta(0),
) -> TimeSplit:
    """Split feature rows into chronological train, validation, and test sets."""
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("fractions must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train_fraction + validation_fraction must leave room for a test split")
    if gap < timedelta(0):
        raise ValueError("gap must not be negative")

    materialized = list(rows)
    for row in materialized:
        if not isinstance(row.get(time_key), datetime):
            raise ValueError(f"every row needs a datetime '{time_key}'")

    timestamps = sorted({row[time_key] for row in materialized})
    train_count = math.floor(len(timestamps) * train_fraction)
    validation_count = math.floor(len(timestamps) * validation_fraction)
    test_count = len(timestamps) - train_count - validation_count
    if min(train_count, validation_count, test_count) < 1:
        raise ValueError("not enough distinct timestamps for three non-empty splits")

    train_times = timestamps[:train_count]
    validation_times = timestamps[train_count:train_count + validation_count]
    test_times = timestamps[train_count + validation_count:]

    validation_times = [t for t in validation_times if t - train_times[-1] > gap]
    if not validation_times:
        raise ValueError("gap leaves no validation rows")
    test_times = [t for t in test_times if t - validation_times[-1] > gap]
    if not test_times:
        raise ValueError("gap leaves no test rows")

    ordered = sorted(materialized, key=lambda row: row[time_key])
    train_set, validation_set, test_set = set(train_times), set(validation_times), set(test_times)
    train = tuple(row for row in ordered if row[time_key] in train_set)
    validation = tuple(row for row in ordered if row[time_key] in validation_set)
    test = tuple(row for row in ordered if row[time_key] in test_set)

    return TimeSplit(
        train=train,
        validation=validation,
        test=test,
        train_end=train_times[-1],
        validation_start=validation_times[0],
        validation_end=validation_times[-1],
        test_start=test_times[0],
        gap=gap,
        purged_row_count=len(materialized) - len(train) - len(validation) - len(test),
    )


def prepare_supervised_splits(
    rows: Sequence[Row] | Iterable[Row],
    *,
    label_key: str = "failure_within_horizon",
    time_key: str = "bucket_start",
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
    gap: timedelta = timedelta(0),
) -> TimeSplit:
    """Run the readiness gate, then split. Raises SupervisedTrainingBlocked if not ready."""
    materialized = list(rows)
    require_supervised_training_ready(materialized, label_key=label_key)
    return chronological_split(
        materialized,
        time_key=time_key,
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
        gap=gap,
    )
