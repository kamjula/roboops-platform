import random
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.services.ml_time_split import chronological_split, prepare_supervised_splits
from app.services.ml_training_readiness import (
    MIN_ROWS,
    SupervisedTrainingBlocked,
    require_supervised_training_ready,
)

START = datetime(2026, 9, 1, tzinfo=timezone.utc)
ROBOTS = [uuid.UUID(int=i) for i in range(1, 4)]


def _rows(hours, robots=ROBOTS, label=None):
    rows = []
    for hour in range(hours):
        for robot_id in robots:
            row = {
                "robot_id": robot_id,
                "bucket_start": START + timedelta(hours=hour),
                "battery_mean": 70.0 + hour % 5,
                "battery_stddev": 1.0,
                "temperature_mean": 38.0,
                "temperature_stddev": 0.5,
            }
            if label is not None:
                row["failure_within_horizon"] = label(hour, robot_id)
            rows.append(row)
    return rows


def _times(rows):
    return [row["bucket_start"] for row in rows]


def test_splits_are_strictly_chronological():
    split = chronological_split(_rows(100))

    assert max(_times(split.train)) < min(_times(split.validation))
    assert max(_times(split.validation)) < min(_times(split.test))
    assert split.train_end == max(_times(split.train))
    assert split.validation_start == min(_times(split.validation))
    assert split.test_start == min(_times(split.test))


def test_uses_requested_fractions_of_distinct_timestamps():
    split = chronological_split(_rows(100), train_fraction=0.6, validation_fraction=0.2)

    assert len(set(_times(split.train))) == 60
    assert len(set(_times(split.validation))) == 20
    assert len(set(_times(split.test))) == 20
    assert split.purged_row_count == 0


def test_rows_sharing_a_timestamp_stay_in_one_split():
    split = chronological_split(_rows(50))

    for part in (split.train, split.validation, split.test):
        for timestamp in set(_times(part)):
            robots = {row["robot_id"] for row in part if row["bucket_start"] == timestamp}
            assert robots == set(ROBOTS)


def test_result_does_not_depend_on_input_order():
    rows = _rows(40)
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)

    first, second = chronological_split(rows), chronological_split(shuffled)

    for a, b in ((first.train, second.train), (first.validation, second.validation), (first.test, second.test)):
        assert {(r["robot_id"], r["bucket_start"]) for r in a} == {(r["robot_id"], r["bucket_start"]) for r in b}


def test_gap_purges_rows_that_a_training_label_could_see():
    horizon = timedelta(hours=24)
    split = chronological_split(_rows(200), gap=horizon)

    assert min(_times(split.validation)) - max(_times(split.train)) > horizon
    assert min(_times(split.test)) - max(_times(split.validation)) > horizon
    assert split.purged_row_count == 2 * 24 * len(ROBOTS)


def test_without_gap_no_rows_are_dropped():
    rows = _rows(30)
    split = chronological_split(rows)

    assert len(split.train) + len(split.validation) + len(split.test) == len(rows)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"train_fraction": 0.0},
        {"validation_fraction": 1.0},
        {"train_fraction": 0.7, "validation_fraction": 0.3},
        {"gap": timedelta(hours=-1)},
    ],
)
def test_rejects_invalid_settings(kwargs):
    with pytest.raises(ValueError):
        chronological_split(_rows(30), **kwargs)


def test_rejects_rows_without_a_timestamp():
    rows = _rows(30)
    rows[5]["bucket_start"] = None

    with pytest.raises(ValueError):
        chronological_split(rows)


def test_rejects_too_few_timestamps_or_a_gap_that_empties_a_split():
    with pytest.raises(ValueError):
        chronological_split(_rows(2))
    with pytest.raises(ValueError):
        chronological_split(_rows(30), gap=timedelta(hours=10))


def test_unlabeled_telemetry_is_blocked_before_splitting():
    with pytest.raises(SupervisedTrainingBlocked) as blocked:
        prepare_supervised_splits(_rows(MIN_ROWS))

    assert "explicit_failure_labels_required" in blocked.value.readiness.reasons


def test_require_ready_returns_result_for_a_valid_labeled_dataset():
    rows = _rows(MIN_ROWS, label=lambda hour, robot: hour % 2 == 0)

    readiness = require_supervised_training_ready(rows)

    assert readiness.ready is True


def test_labeled_dataset_is_split_after_passing_the_gate():
    rows = _rows(MIN_ROWS, label=lambda hour, robot: hour % 2 == 0)

    split = prepare_supervised_splits(rows, gap=timedelta(hours=2))

    assert max(_times(split.train)) < min(_times(split.validation)) < min(_times(split.test))
    assert split.purged_row_count == 2 * 2 * len(ROBOTS)
