"""HTTP observability contract tests that do not require PostgreSQL."""
from __future__ import annotations

import json
import logging
import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_response_generates_request_id_and_metrics_use_route_template():
    response = client.get("/health")
    request_id = response.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f-]{36}", request_id)

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    assert 'roboops_http_requests_total{method="GET",route="/health",status="200"}' in metrics.text
    assert "roboops_http_request_duration_seconds_bucket" in metrics.text
    assert "roboops_http_requests_in_progress" in metrics.text


def test_valid_caller_request_id_is_preserved():
    response = client.get("/health", headers={"X-Request-ID": "trace-20260918_01"})
    assert response.headers["X-Request-ID"] == "trace-20260918_01"


def test_cors_exposes_request_id_to_browser_clients():
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173", "X-Request-ID": "browser-trace"},
    )
    assert response.headers["access-control-expose-headers"] == "X-Request-ID"
    assert response.headers["X-Request-ID"] == "browser-trace"


def test_unsafe_request_id_is_replaced():
    response = client.get("/health", headers={"X-Request-ID": "unsafe id with spaces"})
    assert response.headers["X-Request-ID"] != "unsafe id with spaces"
    assert re.fullmatch(r"[0-9a-f-]{36}", response.headers["X-Request-ID"])


def test_access_log_is_structured_and_correlated(caplog):
    with caplog.at_level(logging.INFO, logger="roboops.http"):
        response = client.get("/health", headers={"X-Request-ID": "correlation-test"})

    record = next(record for record in caplog.records if record.name == "roboops.http")
    payload = json.loads(record.message)
    assert payload == {
        "event": "http_request",
        "request_id": "correlation-test",
        "method": "GET",
        "route": "/health",
        "status": 200,
        "duration_ms": payload["duration_ms"],
    }
    assert payload["duration_ms"] >= 0
    assert response.headers["X-Request-ID"] == payload["request_id"]


def test_unmatched_routes_use_bounded_metric_label():
    assert client.get("/path-that-does-not-exist/123").status_code == 404
    metrics = client.get("/metrics").text
    assert 'route="__unmatched__",status="404"' in metrics
