"""Authenticated, read-only maintenance schedule and history."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import User
from app.models.maintenance_record import MaintenanceRecord
from app.models.maintenance_schedule import MaintenanceSchedule, MaintenanceStatus
from app.models.robot import Robot
from app.models.technician import Technician

router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance"])


class ScheduleItem(BaseModel):
    id: str
    robot_code: str
    robot_name: str
    scheduled_for: datetime
    maintenance_type: str
    status: MaintenanceStatus
    notes: str | None


class RecordItem(BaseModel):
    id: str
    robot_code: str
    robot_name: str
    technician_name: str
    performed_at: datetime
    maintenance_type: str
    description: str | None
    cost_usd: float | None


class MaintenanceWorkspace(BaseModel):
    as_of: datetime
    schedule_total: int
    record_total: int
    schedules: list[ScheduleItem]
    records: list[RecordItem]


@router.get("", response_model=MaintenanceWorkspace)
def read_maintenance(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> MaintenanceWorkspace:
    """Return the first bounded page of each collection, with exact totals."""
    schedules = db.execute(
        select(MaintenanceSchedule, Robot)
        .join(Robot, MaintenanceSchedule.robot_id == Robot.id)
        .order_by(MaintenanceSchedule.scheduled_for.asc(), MaintenanceSchedule.id.asc())
        .limit(limit)
    ).all()
    records = db.execute(
        select(MaintenanceRecord, Robot, Technician)
        .join(Robot, MaintenanceRecord.robot_id == Robot.id)
        .join(Technician, MaintenanceRecord.technician_id == Technician.id)
        .order_by(MaintenanceRecord.performed_at.desc(), MaintenanceRecord.id.asc())
        .limit(limit)
    ).all()
    return MaintenanceWorkspace(
        as_of=datetime.now(timezone.utc),
        schedule_total=db.scalar(select(func.count()).select_from(MaintenanceSchedule)) or 0,
        record_total=db.scalar(select(func.count()).select_from(MaintenanceRecord)) or 0,
        schedules=[
            ScheduleItem(id=str(item.id), robot_code=robot.robot_code, robot_name=robot.name,
                         scheduled_for=item.scheduled_for, maintenance_type=item.maintenance_type,
                         status=item.status, notes=item.notes)
            for item, robot in schedules
        ],
        records=[
            RecordItem(id=str(item.id), robot_code=robot.robot_code, robot_name=robot.name,
                       technician_name=technician.name, performed_at=item.performed_at,
                       maintenance_type=item.maintenance_type, description=item.description,
                       cost_usd=item.cost_usd)
            for item, robot, technician in records
        ],
    )
