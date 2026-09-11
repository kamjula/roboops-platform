"""Versioned Kafka telemetry event contract."""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryEventEnvelope(BaseModel):
    """Strict version-one envelope shared by telemetry producers and consumers."""

    model_config = ConfigDict(extra="forbid")

    event_version: Literal[1]
    event_type: Literal["telemetry.reading"]
    event_id: str = Field(min_length=1)
    sensor_id: uuid.UUID
    observed_at: datetime
    value: float
    source_event_id: str = Field(min_length=1, max_length=128)
    produced_at: datetime

    @field_validator("event_id", "source_event_id", mode="before")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("identifier must not be blank")
        return value.strip()

    @field_validator("value")
    @classmethod
    def validate_finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        return value

    @field_validator("observed_at", "produced_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        return value.astimezone(timezone.utc)

    def serialize(self) -> bytes:
        """Return deterministic compact UTF-8 JSON for Kafka."""
        payload = self.model_dump(mode="json")
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")