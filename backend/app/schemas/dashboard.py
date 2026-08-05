"""Pydantic response schemas for the fleet dashboard endpoints.

These schemas back read-only aggregate endpoints under /api/v1/dashboard.
They intentionally avoid returning untyped dictionaries: every dashboard
endpoint has an explicit, typed response model defined here.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertSeverity


class DashboardSummary(BaseModel):
    """Fleet-wide counters shown on the main dashboard landing view.

    Robot counts use the real RobotStatus enum values (active, idle,
    maintenance, offline, decommissioned) - there is no "warning" or
    "critical" robot status in the schema. "warning"/"critical" only exist
    as AlertSeverity values on the Alert model, and are reported here as
    unresolved-alert counts, not robot states.
    """

    total_robots: int
    active_robots: int
    idle_robots: int
    maintenance_robots: int
    offline_robots: int
    decommissioned_robots: int
    total_sites: int
    open_alerts: int
    warning_alerts: int
    critical_alerts: int
    maintenance_due_count: int
    maintenance_overdue_count: int


class RobotStatusCounts(BaseModel):
    """Robot counts broken down by every real RobotStatus enum value.

    All five enum values are always present, defaulting to zero, even when
    no robots exist in that status (or at all).
    """

    total_robots: int
    active: int
    idle: int
    maintenance: int
    offline: int
    decommissioned: int


class SiteSummaryItem(BaseModel):
    """Robot count for a single site, including sites with zero robots."""

    model_config = ConfigDict(from_attributes=True)

    site_id: uuid.UUID
    site_code: str
    site_name: str
    robot_count: int


class HealthSummaryResponse(BaseModel):
    """Fleet health summary.

    No table in the schema stores a normalized/battery health score for a
    robot - sensor_readings.value is a raw float in whatever unit the
    sensor uses (e.g. degrees, volts, percent, mm/s), and those units are
    not comparable across sensor types. Averaging them together would
    produce a meaningless number, so this endpoint deliberately does not
    compute one. average_health_value is always null and
    health_metric_available is always false until a real normalized health
    field is added to the schema.
    """

    average_health_value: float | None
    health_metric_available: bool
    robot_status_counts: RobotStatusCounts
    maintenance_due_count: int
    maintenance_overdue_count: int


class MaintenanceSummaryResponse(BaseModel):
    """Maintenance due/overdue/completed counts.

    Definitions (see app/services/dashboard_service.py for the query logic):

    - due: a MaintenanceSchedule with status in (scheduled, in_progress)
      AND scheduled_for >= as_of.
    - overdue: a MaintenanceSchedule with status in (scheduled, in_progress)
      AND scheduled_for < as_of.
    - completed: this endpoint reports the total number of MaintenanceRecord
      rows (completed maintenance history), not MaintenanceSchedule rows
      whose status is "completed". A schedule's status can be marked
      completed independently of a record being created for it, so the
      MaintenanceRecord count is used as the authoritative "completed
      maintenance" figure.
    """

    scheduled_count: int
    in_progress_count: int
    due_count: int
    overdue_count: int
    completed_count: int
    as_of: datetime


class LatestAlertItem(BaseModel):
    """A single alert enriched with robot identification for display."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    robot_id: uuid.UUID
    robot_code: str
    robot_name: str
    sensor_id: uuid.UUID | None
    severity: AlertSeverity
    alert_type: str
    message: str
    triggered_at: datetime
    resolved_at: datetime | None
    created_at: datetime
