"""Fleet robots."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RobotStatus(str, enum.Enum):
    ACTIVE = "active"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    DECOMMISSIONED = "decommissioned"


class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    robot_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("robot_models.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    status: Mapped[RobotStatus] = mapped_column(
        Enum(RobotStatus, name="robot_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=RobotStatus.ACTIVE,
    )
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    model: Mapped["RobotModel"] = relationship(back_populates="robots")
    site: Mapped["Site"] = relationship(back_populates="robots")
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="robot", cascade="all, delete-orphan")
    sensor_readings: Mapped[list["SensorReading"]] = relationship(back_populates="robot", cascade="all, delete-orphan")
    maintenance_schedules: Mapped[list["MaintenanceSchedule"]] = relationship(
        back_populates="robot", cascade="all, delete-orphan"
    )
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="robot", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="robot", cascade="all, delete-orphan")
