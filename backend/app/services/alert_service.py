"""Operational alert listing and resolution workflows."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Robot
from app.models.alert import Alert, AlertSeverity
from app.schemas.alert import AlertListItem
from app.services.exceptions import NotFoundError


def _to_list_item(alert: Alert, robot_code: str, robot_name: str) -> AlertListItem:
    return AlertListItem.model_validate(
        {
            "id": alert.id,
            "robot_id": alert.robot_id,
            "robot_code": robot_code,
            "robot_name": robot_name,
            "sensor_id": alert.sensor_id,
            "severity": alert.severity,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "triggered_at": alert.triggered_at,
            "resolved_at": alert.resolved_at,
            "created_at": alert.created_at,
        }
    )


def list_alerts(
    db: Session,
    *,
    state: str = "open",
    severity: AlertSeverity | None = None,
    limit: int = 100,
) -> list[AlertListItem]:
    stmt = select(Alert, Robot.robot_code, Robot.name).join(Robot, Robot.id == Alert.robot_id)
    if state == "open":
        stmt = stmt.where(Alert.resolved_at.is_(None))
    elif state == "resolved":
        stmt = stmt.where(Alert.resolved_at.is_not(None))
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    stmt = stmt.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit)
    return [_to_list_item(alert, robot_code, robot_name) for alert, robot_code, robot_name in db.execute(stmt).all()]


def resolve_alert(db: Session, alert_id: uuid.UUID, *, resolved_at: datetime | None = None) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise NotFoundError(f"Alert {alert_id} not found")
    if alert.resolved_at is None:
        alert.resolved_at = resolved_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)
    return alert
