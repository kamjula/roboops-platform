from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.streaming.telemetry_events import TelemetryEventEnvelope


def valid_event(**overrides):
    values = {
        "event_version": 1,
        "event_type": "telemetry.reading",
        "event_id": "event-1",
        "sensor_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "observed_at": "2026-09-10T12:00:00-04:00",
        "value": 42.5,
        "source_event_id": "source-1",
        "produced_at": "2026-09-10T16:00:01+00:00",
    }
    values.update(overrides)
    return values


def test_valid_event_normalizes_timestamps_and_serializes_deterministically():
    event = TelemetryEventEnvelope(**valid_event())
    assert event.observed_at == datetime(2026, 9, 10, 16, tzinfo=timezone.utc)
    assert event.produced_at == datetime(2026, 9, 10, 16, 0, 1, tzinfo=timezone.utc)
    assert event.serialize() == event.serialize()
    assert event.serialize().decode() == '{"event_id":"event-1","event_type":"telemetry.reading","event_version":1,"observed_at":"2026-09-10T16:00:00Z","produced_at":"2026-09-10T16:00:01Z","sensor_id":"11111111-1111-1111-1111-111111111111","source_event_id":"source-1","value":42.5}'


@pytest.mark.parametrize("field,value", [("event_version", 2), ("event_type", "other")])
def test_version_and_type_are_exact(field, value):
    with pytest.raises(ValidationError):
        TelemetryEventEnvelope(**valid_event(**{field: value}))


@pytest.mark.parametrize("field,value", [("event_id", " "), ("source_event_id", " "), ("sensor_id", "not-a-uuid")])
def test_identifiers_are_validated(field, value):
    with pytest.raises(ValidationError):
        TelemetryEventEnvelope(**valid_event(**{field: value}))


def test_timestamps_require_timezone_and_values_must_be_finite():
    with pytest.raises(ValidationError):
        TelemetryEventEnvelope(**valid_event(observed_at="2026-09-10T16:00:00"))
    with pytest.raises(ValidationError):
        TelemetryEventEnvelope(**valid_event(produced_at="2026-09-10T16:00:00"))
    for value in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValidationError):
            TelemetryEventEnvelope(**valid_event(value=value))


def test_unknown_fields_and_long_source_ids_are_rejected():
    with pytest.raises(ValidationError):
        TelemetryEventEnvelope(**valid_event(extra="forbidden"))
    with pytest.raises(ValidationError):
        TelemetryEventEnvelope(**valid_event(source_event_id="x" * 129))