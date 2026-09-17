import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.dashboard import TelemetryConditionResponse


def _payload():
    now = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
    return {
        "robot_id": uuid.uuid4(),
        "status": "normal",
        "score": 0.5,
        "reason": "condition_score_below_2",
        "feature_z_scores": {"battery_mean": 0.5},
        "baseline_row_count": 20,
        "candidate_bucket_start": now,
        "lookback_hours": 168,
        "as_of": now,
        "window_start": now,
        "condition_model_version": "rms-z-v1",
        "method": "rms_z_score",
        "predicts_failure": False,
    }


@pytest.mark.parametrize("status", ["normal", "warning", "critical", "unknown"])
def test_condition_contract_accepts_supported_statuses(status):
    payload = _payload()
    payload["status"] = status
    assert TelemetryConditionResponse.model_validate(payload).status == status


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "failure_predicted"),
        ("condition_model_version", "fake-model-v99"),
        ("method", "failure_probability"),
        ("predicts_failure", True),
    ],
)
def test_condition_contract_rejects_misleading_semantics(field, value):
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValidationError):
        TelemetryConditionResponse.model_validate(payload)
