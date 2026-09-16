"""Pydantic response schemas for the fleet dashboard endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertSeverity


class DashboardSummary(BaseModel):
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
    total_robots: int
    active: int
    idle: int
    maintenance: int
    offline: int
    decommissioned: int


class SiteSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    site_id: uuid.UUID
    site_code: str
    site_name: str
    robot_count: int


class HealthSummaryResponse(BaseModel):
    average_health_value: float | None
    health_metric_available: bool
    robot_status_counts: RobotStatusCounts
    maintenance_due_count: int
    maintenance_overdue_count: int


class SensorHealthSnapshot(BaseModel):
    state: str
    value: float | None
    unit: str | None
    observed_at: datetime | None
    age_seconds: int | None
    freshness: str
    reason_codes: list[str]


class RobotHealthItem(BaseModel):
    robot_id: uuid.UUID
    robot_code: str
    robot_name: str
    operational_status: str
    health_state: str
    reason_codes: list[str]
    battery: SensorHealthSnapshot | None
    temperature: SensorHealthSnapshot | None


class RobotHealthResponse(BaseModel):
    as_of: datetime
    freshness_threshold_seconds: int
    robots: list[RobotHealthItem]


class MaintenanceSummaryResponse(BaseModel):
    scheduled_count: int
    in_progress_count: int
    due_count: int
    overdue_count: int
    completed_count: int
    as_of: datetime


class LatestAlertItem(BaseModel):
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


class AnomalyEvent(BaseModel):
    reading_id: uuid.UUID
    robot_id: uuid.UUID
    sensor_id: uuid.UUID
    sensor_type: str
    value: float
    severity: str
    reason: str
    recorded_at: datetime


class TelemetryAnomalySummaryResponse(BaseModel):
    as_of: datetime
    window_start: datetime
    lookback_hours: int
    total_readings: int
    severity_counts: dict[str, int]
    reason_counts: dict[str, int]
    anomaly_events: list[AnomalyEvent]
    anomaly_event_limit: int
    anomaly_events_truncated: bool


class StatisticalAnomalyResult(BaseModel):
    reading_id: uuid.UUID
    robot_id: uuid.UUID
    sensor_id: uuid.UUID
    sensor_type: str
    value: float
    recorded_at: datetime
    baseline_sample_count: int
    baseline_mean: float | None
    baseline_stddev: float | None
    z_score: float | None
    status: str
    reason: str


class StatisticalAnomalyResponse(BaseModel):
    as_of: datetime
    window_start: datetime
    baseline_hours: int
    robot_id: uuid.UUID | None
    status_counts: dict[str, int]
    results: list[StatisticalAnomalyResult]


class TelemetryTrendPoint(BaseModel):
    recorded_at: datetime
    value: float


class TelemetryTrendSeries(BaseModel):
    robot_id: uuid.UUID
    robot_code: str
    robot_name: str
    sensor_id: uuid.UUID
    sensor_type: str
    unit: str
    reading_count: int
    min_value: float
    max_value: float
    avg_value: float
    latest_value: float
    latest_recorded_at: datetime
    points: list[TelemetryTrendPoint]


class TelemetryTrendResponse(BaseModel):
    as_of: datetime
    window_start: datetime
    lookback_hours: int
    robot_id: uuid.UUID | None
    total_readings: int
    series_count: int
    point_limit: int
    points_truncated: bool
    series: list[TelemetryTrendSeries]


class TelemetryConditionResponse(BaseModel):
    """Condition/anomaly score from real telemetry history; not failure probability."""

    robot_id: uuid.UUID
    status: str
    score: float | None
    reason: str
    feature_z_scores: dict[str, float]
    baseline_row_count: int
    candidate_bucket_start: datetime | None
    lookback_hours: int
    method: str
    predicts_failure: bool
