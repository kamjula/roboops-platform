"""Pydantic schemas for Site."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SiteBase(BaseModel):
    site_code: str
    name: str
    address: str | None = None
    timezone: str = "UTC"


class SiteCreate(SiteBase):
    pass


class SiteRead(SiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class SiteUpdate(BaseModel):
    site_code: str | None = None
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
