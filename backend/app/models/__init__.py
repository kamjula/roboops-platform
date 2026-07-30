"""Import all ORM models so they register with the shared Base metadata."""
from app.database import Base
from app.models.alert import Alert, AlertSeverity
from app.models.maintenance_record import MaintenanceRecord
from app.models.maintenance_schedule import MaintenanceSchedule, MaintenanceStatus
from app.models.robot import Robot, RobotStatus
from app.models.robot_model import RobotModel
from app.models.sensor import Sensor, SensorType
from app.models.sensor_reading import SensorReading
from app.models.site import Site
from app.models.technician import Technician

__all__ = [
    "Base",
    "Alert",
    "AlertSeverity",
    "MaintenanceRecord",
    "MaintenanceSchedule",
    "MaintenanceStatus",
    "Robot",
    "RobotStatus",
    "RobotModel",
    "Sensor",
    "SensorType",
    "SensorReading",
    "Site",
    "Technician",
]
