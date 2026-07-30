"""Pydantic schemas for Alert."""
import uuid
from datetime import datetime

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
