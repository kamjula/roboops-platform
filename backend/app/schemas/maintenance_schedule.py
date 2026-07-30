"""Pydantic schemas for MaintenanceSchedule."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.maintenance_schedule import MaintenanceStatus


class MaintenanceScheduleBase(BaseModel):
    robot_id: uuid.UUID
    scheduled_for: datetime
    maintenance_type: str
    status: MaintenanceStatus = MaintenanceStatus.SCHEDULED
    notes: str | None = None


class MaintenanceScheduleCreate(MaintenanceScheduleBase):
    pass


class MaintenanceScheduleRead(MaintenanceScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
