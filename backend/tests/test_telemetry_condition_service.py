import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.services.telemetry_condition_service import get_robot_condition


def _feature_row(hour: int, offset: float = 0.0):
    return {
        "robot_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "bucket_start": datetime(2026, 9, 15, hour % 24, tzinfo=timezone.utc),
        "battery_mean": 70.0 + offset,
        "battery_stddev": 1.0 + offset * 0.05,
        "temperature_mean": 35.0 + offset * 0.2,
        "temperature_stddev": 0.8 + offset * 0.02,
    }


def test_returns_unknown_without_complete_feature_rows():
    robot_id = uuid.uuid4()
    with patch(
        "app.services.telemetry_condition_service.build_predictive_feature_dataset",
        return_value={"feature_rows": []},
    ):
        result = get_robot_condition(Mock(), robot_id=robot_id)
    assert result["status"] == "unknown"
    assert result["reason"] == "no_complete_feature_rows"
    assert result["predicts_failure"] is False


def test_requires_preceding_baseline_and_excludes_candidate():
    robot_id = uuid.uuid4()
    rows = [_feature_row(index, float(index)) for index in range(20)]
    with patch(
        "app.services.telemetry_condition_service.build_predictive_feature_dataset",
        return_value={"feature_rows": rows},
    ):
        result = get_robot_condition(Mock(), robot_id=robot_id)
    assert result["status"] == "unknown"
    assert result["reason"] == "minimum_baseline_rows_not_met"
    assert result["baseline_row_count"] == 19


def test_scores_newest_row_against_preceding_real_history():
    robot_id = uuid.uuid4()
    baseline = [_feature_row(index, float(index)) for index in range(20)]
    candidate = _feature_row(21, 60.0)
    rows = baseline + [candidate]
    with patch(
        "app.services.telemetry_condition_service.build_predictive_feature_dataset",
        return_value={"feature_rows": rows},
    ):
        result = get_robot_condition(Mock(), robot_id=robot_id)
    assert result["baseline_row_count"] == 20
    assert result["candidate_bucket_start"] == candidate["bucket_start"]
    assert result["status"] in {"warning", "critical"}
    assert result["score"] is not None
    assert result["predicts_failure"] is False
    assert result["method"] == "rms_z_score"
