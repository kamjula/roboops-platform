"""Pydantic schemas for SensorReading."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SensorReadingBase(BaseModel):
    sensor_id: uuid.UUID
    robot_id: uuid.UUID
    recorded_at: datetime
    value: float


class SensorReadingCreate(SensorReadingBase):
    pass


class SensorReadingRead(SensorReadingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
