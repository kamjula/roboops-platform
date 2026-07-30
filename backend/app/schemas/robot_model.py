"""Pydantic schemas for RobotModel."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RobotModelBase(BaseModel):
    model_code: str
    manufacturer: str
    name: str
    category: str


class RobotModelCreate(RobotModelBase):
    pass


class RobotModelRead(RobotModelBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
