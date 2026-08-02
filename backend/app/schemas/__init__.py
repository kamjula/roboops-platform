"""Pydantic schema exports for the RoboOps API."""
from app.schemas.alert import AlertBase, AlertCreate, AlertRead
from app.schemas.maintenance_record import MaintenanceRecordBase, MaintenanceRecordCreate, MaintenanceRecordRead
from app.schemas.maintenance_schedule import (
    MaintenanceScheduleBase,
    MaintenanceScheduleCreate,
    MaintenanceScheduleRead,
)
from app.schemas.robot import RobotBase, RobotCreate, RobotRead, RobotUpdate
from app.schemas.robot_model import RobotModelBase, RobotModelCreate, RobotModelRead, RobotModelUpdate
from app.schemas.sensor import SensorBase, SensorCreate, SensorRead
from app.schemas.sensor_reading import SensorReadingBase, SensorReadingCreate, SensorReadingRead
from app.schemas.site import SiteBase, SiteCreate, SiteRead, SiteUpdate
from app.schemas.technician import TechnicianBase, TechnicianCreate, TechnicianRead

__all__ = [
    "AlertBase",
    "AlertCreate",
    "AlertRead",
    "MaintenanceRecordBase",
    "MaintenanceRecordCreate",
    "MaintenanceRecordRead",
    "MaintenanceScheduleBase",
    "MaintenanceScheduleCreate",
    "MaintenanceScheduleRead",
    "RobotBase",
    "RobotCreate",
    "RobotRead",
    "RobotUpdate",
    "RobotModelBase",
    "RobotModelCreate",
    "RobotModelRead",
    "RobotModelUpdate",
    "SensorBase",
    "SensorCreate",
    "SensorRead",
    "SensorReadingBase",
    "SensorReadingCreate",
    "SensorReadingRead",
    "SiteBase",
    "SiteCreate",
    "SiteRead",
    "SiteUpdate",
    "TechnicianBase",
    "TechnicianCreate",
    "TechnicianRead",
]
