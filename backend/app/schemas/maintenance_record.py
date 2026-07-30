"""Pydantic schemas for MaintenanceRecord."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaintenanceRecordBase(BaseModel):
    robot_id: uuid.UUID
    technician_id: uuid.UUID
    schedule_id: uuid.UUID | None = None
    performed_at: datetime
    maintenance_type: str
    description: str | None = None
    cost_usd: float | None = None


class MaintenanceRecordCreate(MaintenanceRecordBase):
    pass


class MaintenanceRecordRead(MaintenanceRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
