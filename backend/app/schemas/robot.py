"""Pydantic schemas for Robot."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.robot import RobotStatus


class RobotBase(BaseModel):
    robot_code: str
    name: str
    serial_number: str
    model_id: uuid.UUID
    site_id: uuid.UUID
    status: RobotStatus = RobotStatus.ACTIVE
    installed_at: datetime


class RobotCreate(RobotBase):
    pass


class RobotRead(RobotBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
