"""Read-only fleet dashboard endpoints.

All six endpoints return typed Pydantic response models (see
app.schemas.dashboard) rather than untyped dictionaries.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import (
    DashboardSummary,
    HealthSummaryResponse,
    LatestAlertItem,
    MaintenanceSummaryResponse,
    RobotStatusCounts,
    SiteSummaryItem,
)
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def read_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    """Fleet-wide counters: robot statuses, sites, open alerts, maintenance due."""
    return dashboard_service.get_dashboard_summary(db)


@router.get("/robot-status", response_model=RobotStatusCounts)
def read_robot_status(db: Session = Depends(get_db)) -> RobotStatusCounts:
    """Robot counts for every real RobotStatus enum value (zero-filled)."""
    return dashboard_service.get_robot_status_breakdown(db)


@router.get("/latest-alerts", response_model=list[LatestAlertItem])
def read_latest_alerts(
    limit: int = Query(10, ge=1, le=100, description="Max number of alerts to return (1-100)."),
    db: Session = Depends(get_db),
) -> list[LatestAlertItem]:
    """The most recent alerts fleet-wide, ordered by created_at DESC, id DESC."""
    return dashboard_service.get_latest_alerts(db, limit=limit)


@router.get("/health-summary", response_model=HealthSummaryResponse)
def read_health_summary(db: Session = Depends(get_db)) -> HealthSummaryResponse:
    """Fleet health summary. No normalized health score exists in the schema."""
    return dashboard_service.get_health_summary(db)


@router.get("/site-summary", response_model=list[SiteSummaryItem])
def read_site_summary(db: Session = Depends(get_db)) -> list[SiteSummaryItem]:
    """Per-site robot counts, including sites with zero robots."""
    return dashboard_service.get_site_summary(db)


@router.get("/maintenance-summary", response_model=MaintenanceSummaryResponse)
def read_maintenance_summary(db: Session = Depends(get_db)) -> MaintenanceSummaryResponse:
    """Maintenance due/overdue/completed counts."""
    return dashboard_service.get_maintenance_summary(db)
