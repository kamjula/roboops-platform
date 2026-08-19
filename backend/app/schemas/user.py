from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class UserCreate(UserBase):
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class UserMe(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
