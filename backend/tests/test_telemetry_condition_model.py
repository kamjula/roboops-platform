import math

import pytest

from app.services.telemetry_condition_model import (
    MIN_BASELINE_ROWS,
    fit_feature_baseline,
    score_condition,
)


def _row(battery_mean=70.0, battery_stddev=1.0, temperature_mean=35.0, temperature_stddev=1.0):
    return {
        "battery_mean": battery_mean,
        "battery_stddev": battery_stddev,
        "temperature_mean": temperature_mean,
        "temperature_stddev": temperature_stddev,
    }


def test_requires_real_minimum_baseline_rows():
    with pytest.raises(ValueError, match="minimum_baseline_rows_not_met"):
        fit_feature_baseline([_row() for _ in range(MIN_BASELINE_ROWS - 1)])


def test_rejects_incomplete_baseline_features():
    rows = [_row(70.0 + index) for index in range(MIN_BASELINE_ROWS)]
    rows[0]["temperature_mean"] = None
    with pytest.raises(ValueError, match="incomplete_required_features"):
        fit_feature_baseline(rows)


def test_zero_variance_baseline_returns_unknown():
    baseline = fit_feature_baseline([_row() for _ in range(MIN_BASELINE_ROWS)])
    result = score_condition(_row(), baseline)
    assert result.status == "unknown"
    assert result.score is None
    assert result.reason == "baseline_variance_unavailable"


def test_scores_unusual_condition_without_failure_claim():
    rows = [
        _row(
            battery_mean=60.0 + index,
            battery_stddev=1.0 + index * 0.1,
            temperature_mean=30.0 + index * 0.5,
            temperature_stddev=0.5 + index * 0.05,
        )
        for index in range(MIN_BASELINE_ROWS)
    ]
    baseline = fit_feature_baseline(rows)
    result = score_condition(
        _row(
            battery_mean=10.0,
            battery_stddev=10.0,
            temperature_mean=60.0,
            temperature_stddev=8.0,
        ),
        baseline,
    )
    assert result.status in {"warning", "critical"}
    assert result.score is not None
    assert math.isfinite(result.score)
    assert set(result.feature_z_scores) == {
        "battery_mean",
        "battery_stddev",
        "temperature_mean",
        "temperature_stddev",
    }


def test_missing_scored_feature_returns_unknown():
    rows = [
        _row(60.0 + index, 1.0 + index * 0.1, 30.0 + index * 0.5, 0.5 + index * 0.05)
        for index in range(MIN_BASELINE_ROWS)
    ]
    baseline = fit_feature_baseline(rows)
    candidate = _row()
    candidate["battery_mean"] = None
    result = score_condition(candidate, baseline)
    assert result.status == "unknown"
    assert result.reason == "incomplete_required_features"
