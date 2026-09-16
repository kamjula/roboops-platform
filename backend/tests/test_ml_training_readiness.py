from app.services.ml_training_readiness import (
    MIN_NEGATIVE_LABELS,
    MIN_POSITIVE_LABELS,
    MIN_ROWS,
    assess_supervised_training_readiness,
)


def _row(label=None):
    row = {
        "battery_mean": 72.0,
        "battery_stddev": 1.5,
        "temperature_mean": 38.0,
        "temperature_stddev": 0.8,
    }
    if label is not None:
        row["failure_within_horizon"] = label
    return row


def test_refuses_unlabeled_telemetry_features():
    result = assess_supervised_training_readiness([_row() for _ in range(MIN_ROWS)])

    assert result.ready is False
    assert "explicit_failure_labels_required" in result.reasons
    assert result.labeled_row_count == 0


def test_refuses_small_or_single_class_dataset():
    rows = [_row(True) for _ in range(MIN_POSITIVE_LABELS)]
    result = assess_supervised_training_readiness(rows)

    assert result.ready is False
    assert "insufficient_feature_rows" in result.reasons
    assert "insufficient_negative_labels" in result.reasons


def test_refuses_missing_required_feature():
    rows = [_row(False) for _ in range(MIN_ROWS)]
    rows[0]["temperature_stddev"] = None
    result = assess_supervised_training_readiness(rows)

    assert result.ready is False
    assert "incomplete_required_features" in result.reasons


def test_accepts_only_explicit_complete_balanced_minimum_dataset():
    positive = max(MIN_POSITIVE_LABELS, MIN_ROWS // 2)
    negative = max(MIN_NEGATIVE_LABELS, MIN_ROWS - positive)
    rows = [_row(True) for _ in range(positive)] + [_row(False) for _ in range(negative)]

    result = assess_supervised_training_readiness(rows)

    assert result.ready is True
    assert result.reasons == ()
    assert result.row_count >= MIN_ROWS
    assert result.positive_labels >= MIN_POSITIVE_LABELS
    assert result.negative_labels >= MIN_NEGATIVE_LABELS
