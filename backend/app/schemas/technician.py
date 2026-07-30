"""Pydantic schemas for Technician."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class TechnicianBase(BaseModel):
    technician_code: str
    name: str
    email: EmailStr
    phone: str | None = None


class TechnicianCreate(TechnicianBase):
    pass


class TechnicianRead(TechnicianBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
