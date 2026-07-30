"""Pydantic schemas for Sensor."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.sensor import SensorType


class SensorBase(BaseModel):
    robot_id: uuid.UUID
    sensor_code: str
    sensor_type: SensorType
    unit: str


class SensorCreate(SensorBase):
    pass


class SensorRead(SensorBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
