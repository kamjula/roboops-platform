"""Operational alert listing and resolution workflows."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Robot
from app.models.alert import Alert, AlertSeverity
from app.schemas.alert import AlertListItem, ConditionAlertSyncResponse
from app.services import telemetry_condition_service
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


CONDITION_ALERT_TYPE = "telemetry_condition"
_CONDITION_SYNC_LOCK_ID = 734_221_409


def _condition_message(result: dict, model_version: str) -> str:
    score = result.get("score")
    score_text = "unavailable" if score is None else f"{score:.3f}"
    return (
        f"Telemetry condition is {result['status']} (score={score_text}, "
        f"model={model_version}, reason={result['reason']}). "
        "This is an anomaly signal, not a failure prediction."
    )


def sync_condition_alerts(
    db: Session,
    *,
    lookback_hours: int = 168,
    as_of: datetime | None = None,
) -> ConditionAlertSyncResponse:
    """Synchronize fleet condition signals to one open alert per robot.

    Warning and critical signals create or update an alert. A normal signal
    resolves it. Unknown signals deliberately leave existing alerts untouched.
    PostgreSQL's transaction-level advisory lock serializes fleet-wide syncs;
    the partial unique index remains the final duplicate guard.
    """
    db.execute(select(func.pg_advisory_xact_lock(_CONDITION_SYNC_LOCK_ID)))
    conditions = telemetry_condition_service.get_fleet_conditions(
        db,
        as_of=as_of,
        lookback_hours=lookback_hours,
    )
    open_alerts = db.execute(
        select(Alert).where(
            Alert.alert_type == CONDITION_ALERT_TYPE,
            Alert.resolved_at.is_(None),
        )
    ).scalars().all()
    open_by_robot = {alert.robot_id: alert for alert in open_alerts}

    counts = {"created": 0, "updated": 0, "resolved": 0, "unchanged": 0, "unknown": 0}
    for result in conditions["robots"]:
        robot_id = result["robot_id"]
        signal = result["status"]
        existing = open_by_robot.get(robot_id)

        if signal == "unknown":
            counts["unknown"] += 1
            continue
        if signal == "normal":
            if existing is None:
                counts["unchanged"] += 1
            else:
                existing.resolved_at = conditions["as_of"]
                counts["resolved"] += 1
            continue

        severity = AlertSeverity.CRITICAL if signal == "critical" else AlertSeverity.WARNING
        message = _condition_message(result, conditions["condition_model_version"])
        if existing is None:
            alert = Alert(
                robot_id=robot_id,
                severity=severity,
                alert_type=CONDITION_ALERT_TYPE,
                message=message,
                triggered_at=result.get("candidate_bucket_start") or conditions["as_of"],
            )
            db.add(alert)
            open_by_robot[robot_id] = alert
            counts["created"] += 1
        elif existing.severity != severity or existing.message != message:
            existing.severity = severity
            existing.message = message
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1

    db.commit()
    return ConditionAlertSyncResponse(
        as_of=conditions["as_of"],
        lookback_hours=lookback_hours,
        condition_model_version=conditions["condition_model_version"],
        method=conditions["method"],
        predicts_failure=False,
        evaluated=len(conditions["robots"]),
        **counts,
    )
