"""Sensors attached to robots."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SensorType(str, enum.Enum):
    TEMPERATURE = "temperature"
    BATTERY = "battery"
    VIBRATION = "vibration"
    MOTOR_LOAD = "motor_load"
    NAVIGATION_ERROR = "navigation_error"


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    robot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("robots.id"), nullable=False)
    sensor_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    sensor_type: Mapped[SensorType] = mapped_column(
        Enum(SensorType, name="sensor_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    robot: Mapped["Robot"] = relationship(back_populates="sensors")
    readings: Mapped[list["SensorReading"]] = relationship(back_populates="sensor", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="sensor")
