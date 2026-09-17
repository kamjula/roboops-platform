"""Read-only fleet dashboard endpoints.

All endpoints return typed Pydantic response models (see
app.schemas.dashboard) rather than untyped dictionaries.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.schemas.dashboard import (
    DashboardSummary,
    FleetTelemetryConditionResponse,
    HealthSummaryResponse,
    LatestAlertItem,
    MaintenanceSummaryResponse,
    RobotHealthResponse,
    RobotStatusCounts,
    SiteSummaryItem,
    StatisticalAnomalyResponse,
    TelemetryAnomalySummaryResponse,
    TelemetryConditionResponse,
    TelemetryTrendResponse,
)
from app.services import dashboard_service
from app.services import robot_health_service
from app.services import statistical_anomaly_service
from app.services import telemetry_anomaly_service
from app.services import telemetry_condition_service
from app.services import telemetry_trend_service

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/summary", response_model=DashboardSummary)
def read_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    return dashboard_service.get_dashboard_summary(db)


@router.get("/robot-status", response_model=RobotStatusCounts)
def read_robot_status(db: Session = Depends(get_db)) -> RobotStatusCounts:
    return dashboard_service.get_robot_status_breakdown(db)


@router.get("/latest-alerts", response_model=list[LatestAlertItem])
def read_latest_alerts(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[LatestAlertItem]:
    return dashboard_service.get_latest_alerts(db, limit=limit)


@router.get("/health-summary", response_model=HealthSummaryResponse)
def read_health_summary(db: Session = Depends(get_db)) -> HealthSummaryResponse:
    return dashboard_service.get_health_summary(db)


@router.get("/robot-health", response_model=RobotHealthResponse)
def read_robot_health(db: Session = Depends(get_db)) -> RobotHealthResponse:
    return robot_health_service.get_robot_health(db)


@router.get("/telemetry-anomalies", response_model=TelemetryAnomalySummaryResponse)
def read_telemetry_anomalies(
    lookback_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
) -> TelemetryAnomalySummaryResponse:
    return telemetry_anomaly_service.get_anomaly_summary(db, lookback_hours=lookback_hours)


@router.get("/statistical-anomalies", response_model=StatisticalAnomalyResponse)
def read_statistical_anomalies(
    baseline_hours: int = Query(
        24,
        ge=1,
        le=168,
        description="Historical baseline window in hours (1-168).",
    ),
    robot_id: uuid.UUID | None = Query(None, description="Optional robot UUID filter."),
    db: Session = Depends(get_db),
) -> StatisticalAnomalyResponse:
    """Score latest persisted readings against their preceding real history."""
    return statistical_anomaly_service.get_statistical_anomalies(
        db,
        baseline_hours=baseline_hours,
        robot_id=robot_id,
    )


@router.get("/telemetry-trends", response_model=TelemetryTrendResponse)
def read_telemetry_trends(
    lookback_hours: int = Query(24, ge=1, le=168),
    robot_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
) -> TelemetryTrendResponse:
    return telemetry_trend_service.get_telemetry_trends(
        db,
        lookback_hours=lookback_hours,
        robot_id=robot_id,
    )


@router.get("/telemetry-condition", response_model=TelemetryConditionResponse)
def read_telemetry_condition(
    robot_id: uuid.UUID = Query(..., description="Robot UUID to score."),
    lookback_hours: int = Query(168, ge=21, le=168),
    db: Session = Depends(get_db),
) -> TelemetryConditionResponse:
    """Score one robot's newest complete hourly feature row against prior history.

    This is an unsupervised condition/anomaly score, not a failure probability
    or remaining-useful-life prediction.
    """
    return telemetry_condition_service.get_robot_condition(
        db,
        robot_id=robot_id,
        lookback_hours=lookback_hours,
    )


@router.get("/telemetry-conditions", response_model=FleetTelemetryConditionResponse)
def read_fleet_telemetry_conditions(
    lookback_hours: int = Query(168, ge=21, le=168),
    db: Session = Depends(get_db),
) -> FleetTelemetryConditionResponse:
    """Score the fleet with one set-based telemetry feature extraction.

    Results remain condition/anomaly signals only. No failure probability,
    RUL, model accuracy, or other predictive metric is fabricated.
    """
    return telemetry_condition_service.get_fleet_conditions(
        db,
        lookback_hours=lookback_hours,
    )


@router.get("/site-summary", response_model=list[SiteSummaryItem])
def read_site_summary(db: Session = Depends(get_db)) -> list[SiteSummaryItem]:
    return dashboard_service.get_site_summary(db)


@router.get("/maintenance-summary", response_model=MaintenanceSummaryResponse)
def read_maintenance_summary(db: Session = Depends(get_db)) -> MaintenanceSummaryResponse:
    return dashboard_service.get_maintenance_summary(db)
