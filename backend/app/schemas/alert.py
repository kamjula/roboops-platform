"""Pydantic schemas for Alert."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertSeverity


class AlertBase(BaseModel):
    robot_id: uuid.UUID
    sensor_id: uuid.UUID | None = None
    severity: AlertSeverity
    alert_type: str
    message: str
    triggered_at: datetime
    resolved_at: datetime | None = None


class AlertCreate(AlertBase):
    pass


class AlertRead(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class AlertListItem(AlertRead):
    """Alert response enriched with robot identity in the same query."""

    robot_code: str
    robot_name: str


class ConditionAlertSyncResponse(BaseModel):
    """Auditable result of translating condition signals into operational alerts."""

    as_of: datetime
    lookback_hours: int
    condition_model_version: Literal["rms-z-v1"]
    method: Literal["rms_z_score"]
    predicts_failure: Literal[False]
    evaluated: int
    created: int
    updated: int
    resolved: int
    unchanged: int
    unknown: int
