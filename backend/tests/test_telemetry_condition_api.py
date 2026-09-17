import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

AS_OF = datetime(2026, 9, 16, 15, tzinfo=timezone.utc)
WINDOW_START = AS_OF - timedelta(hours=168)


def _response(robot_id: uuid.UUID):
    return {
        "robot_id": robot_id,
        "status": "normal",
        "score": 0.75,
        "reason": "condition_score_below_2",
        "feature_z_scores": {
            "battery_mean": 0.5,
            "battery_stddev": 0.25,
            "temperature_mean": -0.5,
            "temperature_stddev": 0.25,
        },
        "baseline_row_count": 20,
        "candidate_bucket_start": datetime(2026, 9, 16, 14, tzinfo=timezone.utc),
        "lookback_hours": 168,
        "as_of": AS_OF,
        "window_start": WINDOW_START,
        "condition_model_version": "rms-z-v1",
        "method": "rms_z_score",
        "predicts_failure": False,
    }


def test_telemetry_condition_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get(
        "/api/v1/dashboard/telemetry-condition",
        params={"robot_id": str(uuid.uuid4())},
    )
    assert response.status_code == 401


def test_telemetry_condition_validates_query(client):
    robot_id = uuid.uuid4()
    assert client.get(
        "/api/v1/dashboard/telemetry-condition",
        params={"robot_id": str(robot_id), "lookback_hours": 20},
    ).status_code == 422
    assert client.get(
        "/api/v1/dashboard/telemetry-condition",
        params={"robot_id": str(robot_id), "lookback_hours": 169},
    ).status_code == 422


def test_telemetry_condition_returns_typed_truthful_contract(client):
    robot_id = uuid.uuid4()
    with patch(
        "app.routers.dashboard.telemetry_condition_service.get_robot_condition",
        return_value=_response(robot_id),
    ) as service:
        response = client.get(
            "/api/v1/dashboard/telemetry-condition",
            params={"robot_id": str(robot_id), "lookback_hours": 168},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["robot_id"] == str(robot_id)
    assert payload["method"] == "rms_z_score"
    assert payload["condition_model_version"] == "rms-z-v1"
    assert payload["as_of"] == AS_OF.isoformat().replace("+00:00", "Z")
    assert payload["window_start"] == WINDOW_START.isoformat().replace("+00:00", "Z")
    assert payload["predicts_failure"] is False
    assert payload["baseline_row_count"] == 20
    service.assert_called_once()
