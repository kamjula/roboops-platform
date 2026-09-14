from __future__ import annotations

import os

import pytest

from app.routers import dashboard as dashboard_router


pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not set.",
)


def test_telemetry_anomalies_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get(
        "/api/v1/dashboard/telemetry-anomalies"
    )

    assert response.status_code == 401


def test_telemetry_anomalies_authenticated(client, monkeypatch):
    expected = {
        "as_of": "2026-09-11T12:00:00Z",
        "window_start": "2026-09-10T12:00:00Z",
        "lookback_hours": 24,
        "total_readings": 3,
        "severity_counts": {
            "normal": 1,
            "warning": 1,
            "critical": 1,
            "unknown": 0,
        },
        "reason_counts": {
            "battery_low": 1,
            "temperature_critical": 1,
        },
        "anomaly_events": [],
    }

    monkeypatch.setattr(
        dashboard_router.telemetry_anomaly_service,
        "get_anomaly_summary",
        lambda db, lookback_hours=24: expected,
    )

    response = client.get(
        "/api/v1/dashboard/telemetry-anomalies"
    )

    assert response.status_code == 200

    body = response.json()
    assert body["lookback_hours"] == 24
    assert body["total_readings"] == 3
    assert body["severity_counts"]["critical"] == 1


def test_telemetry_anomalies_validates_lookback(client):
    response = client.get(
        "/api/v1/dashboard/telemetry-anomalies?lookback_hours=0"
    )

    assert response.status_code == 422
