"""Completed maintenance history."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    robot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("robots.id"), nullable=False)
    technician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("technicians.id"), nullable=False)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_schedules.id"), nullable=True
    )
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    robot: Mapped["Robot"] = relationship(back_populates="maintenance_records")
    technician: Mapped["Technician"] = relationship(back_populates="maintenance_records")
    schedule: Mapped["MaintenanceSchedule | None"] = relationship(back_populates="maintenance_records")
