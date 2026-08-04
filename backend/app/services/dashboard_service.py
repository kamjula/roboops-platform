"""Query logic for the fleet dashboard endpoints.

All aggregation here is based only on real columns and enum values that
exist in app.models - see the schema docstrings in app.schemas.dashboard
for the definitions of "due", "overdue", "completed", and why no
normalized health score is computed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity
from app.models.maintenance_record import MaintenanceRecord
from app.models.maintenance_schedule import MaintenanceSchedule, MaintenanceStatus
from app.models.robot import Robot, RobotStatus
from app.models.site import Site
from app.schemas.dashboard import (
    DashboardSummary,
    HealthSummaryResponse,
    LatestAlertItem,
    MaintenanceSummaryResponse,
    RobotStatusCounts,
    SiteSummaryItem,
)

# Maintenance schedule statuses that represent work that has not finished
# yet, and can therefore still be "due" or "overdue". Cancelled and
# completed schedules are intentionally excluded from both counts.
_OPEN_MAINTENANCE_STATUSES = (MaintenanceStatus.SCHEDULED, MaintenanceStatus.IN_PROGRESS)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _robot_status_counts(db: Session) -> dict[RobotStatus, int]:
    """Robot counts grouped by status, with every enum value present."""
    counts: dict[RobotStatus, int] = {status: 0 for status in RobotStatus}
    stmt = select(Robot.status, func.count(Robot.id)).group_by(Robot.status)
    for status, count in db.execute(stmt).all():
        counts[status] = count
    return counts


def _open_alert_severity_counts(db: Session) -> dict[AlertSeverity, int]:
    """Unresolved (resolved_at IS NULL) alert counts grouped by severity."""
    counts: dict[AlertSeverity, int] = {severity: 0 for severity in AlertSeverity}
    stmt = (
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.resolved_at.is_(None))
        .group_by(Alert.severity)
    )
    for severity, count in db.execute(stmt).all():
        counts[severity] = count
    return counts


def get_maintenance_due_count(db: Session, as_of: datetime | None = None) -> int:
    """Count schedules that are still outstanding and not yet overdue.

    due = status in (scheduled, in_progress) AND scheduled_for >= as_of.
    """
    as_of = as_of or _utc_now()
    stmt = select(func.count(MaintenanceSchedule.id)).where(
        MaintenanceSchedule.status.in_(_OPEN_MAINTENANCE_STATUSES),
        MaintenanceSchedule.scheduled_for >= as_of,
    )
    return db.execute(stmt).scalar_one()


def get_maintenance_overdue_count(db: Session, as_of: datetime | None = None) -> int:
    """Count schedules whose scheduled date has passed without completion.

    overdue = status in (scheduled, in_progress) AND scheduled_for < as_of.
    """
    as_of = as_of or _utc_now()
    stmt = select(func.count(MaintenanceSchedule.id)).where(
        MaintenanceSchedule.status.in_(_OPEN_MAINTENANCE_STATUSES),
        MaintenanceSchedule.scheduled_for < as_of,
    )
    return db.execute(stmt).scalar_one()

def get_maintenance_scheduled_count(db: Session) -> int:
    """Count of maintenance schedules currently in the scheduled status,
    regardless of whether scheduled_for is due or overdue.
    """
    stmt = select(func.count(MaintenanceSchedule.id)).where(
        MaintenanceSchedule.status == MaintenanceStatus.SCHEDULED,
    )
    return db.execute(stmt).scalar_one()

def get_maintenance_in_progress_count(db: Session) -> int:
    """Count of maintenance schedules currently in the in_progress status,
    regardless of whether scheduled_for is due or overdue.
    """
    stmt = select(func.count(MaintenanceSchedule.id)).where(
        MaintenanceSchedule.status == MaintenanceStatus.IN_PROGRESS,
    )
    return db.execute(stmt).scalar_one()

def get_maintenance_completed_count(db: Session) -> int:
    """Total completed maintenance history rows (MaintenanceRecord count).

    See MaintenanceSummaryResponse's docstring for why MaintenanceRecord
    rows, rather than MaintenanceSchedule rows with status "completed",
    are used as the authoritative "completed maintenance" figure.
    """
    return db.execute(select(func.count(MaintenanceRecord.id))).scalar_one()


def get_dashboard_summary(db: Session) -> DashboardSummary:
    status_counts = _robot_status_counts(db)
    severity_counts = _open_alert_severity_counts(db)
    total_sites = db.execute(select(func.count(Site.id))).scalar_one()
    return DashboardSummary(
        total_robots=sum(status_counts.values()),
        active_robots=status_counts[RobotStatus.ACTIVE],
        idle_robots=status_counts[RobotStatus.IDLE],
        maintenance_robots=status_counts[RobotStatus.MAINTENANCE],
        offline_robots=status_counts[RobotStatus.OFFLINE],
        decommissioned_robots=status_counts[RobotStatus.DECOMMISSIONED],
        total_sites=total_sites,
        open_alerts=sum(severity_counts.values()),
        warning_alerts=severity_counts[AlertSeverity.WARNING],
        critical_alerts=severity_counts[AlertSeverity.CRITICAL],
        maintenance_due_count=get_maintenance_due_count(db),
        maintenance_overdue_count=get_maintenance_overdue_count(db),
    )


def get_robot_status_breakdown(db: Session) -> RobotStatusCounts:
    status_counts = _robot_status_counts(db)
    return RobotStatusCounts(
        total_robots=sum(status_counts.values()),
        active=status_counts[RobotStatus.ACTIVE],
        idle=status_counts[RobotStatus.IDLE],
        maintenance=status_counts[RobotStatus.MAINTENANCE],
        offline=status_counts[RobotStatus.OFFLINE],
        decommissioned=status_counts[RobotStatus.DECOMMISSIONED],
    )


def get_site_summary(db: Session) -> list[SiteSummaryItem]:
    """Per-site robot counts, including sites with zero robots.

    Uses a LEFT OUTER JOIN from Site to Robot so sites without any robots
    still appear with robot_count = 0. Ordered deterministically by
    site_code, then site_id.
    """
    stmt = (
        select(Site.id, Site.site_code, Site.name, func.count(Robot.id))
        .outerjoin(Robot, Robot.site_id == Site.id)
        .group_by(Site.id, Site.site_code, Site.name)
        .order_by(Site.site_code.asc(), Site.id.asc())
    )
    return [
        SiteSummaryItem(site_id=site_id, site_code=site_code, site_name=name, robot_count=robot_count)
        for site_id, site_code, name, robot_count in db.execute(stmt).all()
    ]


def get_health_summary(db: Session, as_of: datetime | None = None) -> HealthSummaryResponse:
    """Fleet health summary.

    average_health_value is always null and health_metric_available is
    always false: no table stores a normalized/battery health score, and
    raw sensor_readings.value cannot be honestly averaged across sensors
    that use different units (temperature, volts, vibration, etc.).
    """
    return HealthSummaryResponse(
        average_health_value=None,
        health_metric_available=False,
        robot_status_counts=get_robot_status_breakdown(db),
        maintenance_due_count=get_maintenance_due_count(db, as_of),
        maintenance_overdue_count=get_maintenance_overdue_count(db, as_of),
    )


def get_maintenance_summary(db: Session, as_of: datetime | None = None) -> MaintenanceSummaryResponse:
    as_of = as_of or _utc_now()
    return MaintenanceSummaryResponse(
        scheduled_count=get_maintenance_scheduled_count(db),
        in_progress_count=get_maintenance_in_progress_count(db),
        due_count=get_maintenance_due_count(db, as_of),
        overdue_count=get_maintenance_overdue_count(db, as_of),
        completed_count=get_maintenance_completed_count(db),
        as_of=as_of,
    )


def get_latest_alerts(db: Session, limit: int = 10) -> list[LatestAlertItem]:
    """The most recent alerts fleet-wide, newest first.

    Ordered by created_at DESC, id DESC as a stable tie-breaker so alerts
    inserted at the same instant still sort deterministically. Robot is
    joined in the same query (no N+1) to include robot_code/robot_name.
    """
    stmt = (
        select(Alert, Robot.robot_code, Robot.name)
        .join(Robot, Robot.id == Alert.robot_id)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(limit)
    )
    items: list[LatestAlertItem] = []
    for alert, robot_code, robot_name in db.execute(stmt).all():
        items.append(
            LatestAlertItem(
                id=alert.id,
                robot_id=alert.robot_id,
                robot_code=robot_code,
                robot_name=robot_name,
                sensor_id=alert.sensor_id,
                severity=alert.severity,
                alert_type=alert.alert_type,
                message=alert.message,
                triggered_at=alert.triggered_at,
                resolved_at=alert.resolved_at,
                created_at=alert.created_at,
            )
        )
    return items
