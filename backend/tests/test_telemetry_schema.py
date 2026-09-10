from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.telemetry import TelemetryReadingCreate


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_telemetry_values_are_rejected(value):
    with pytest.raises(ValidationError, match="value must be finite"):
        TelemetryReadingCreate(
            sensor_id=uuid.uuid4(),
            value=value,
            observed_at="2025-01-01T00:00:00Z",
            source_event_id="x",
        )
