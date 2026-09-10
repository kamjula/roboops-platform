"""Schemas for authenticated telemetry ingestion and queries."""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryReadingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_id: uuid.UUID
    value: float
    observed_at: datetime
    source_event_id: str = Field(max_length=128)

    @field_validator("value")
    @classmethod
    def validate_finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        return value

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include timezone information")
        normalized = value.astimezone(timezone.utc)
        if normalized > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("observed_at is too far in the future")
        return normalized

    @field_validator("source_event_id", mode="before")
    @classmethod
    def validate_source_event_id(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("source_event_id must be a string")
        value = value.strip()
        if not value:
            raise ValueError("source_event_id must not be blank")
        if len(value) > 128:
            raise ValueError("source_event_id must be at most 128 characters")
        return value


class TelemetryReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sensor_id: uuid.UUID
    robot_id: uuid.UUID
    value: float
    observed_at: datetime
    source_event_id: str | None
    created_at: datetime


class TelemetryReadingResponse(TelemetryReadingRead):
    pass