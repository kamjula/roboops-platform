"""Readiness integration coverage against the dedicated PostgreSQL test DB."""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is not set.",
)


def test_readiness_executes_real_database_query(unauthenticated_client):
    response = unauthenticated_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}
