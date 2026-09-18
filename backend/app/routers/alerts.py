"""Authenticated alert operations."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.database import get_db
from app.models import User, UserRole
from app.models.alert import AlertSeverity
from app.schemas.alert import AlertListItem, AlertRead
from app.services import alert_service
from app.services.exceptions import NotFoundError

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertListItem])
def read_alerts(
    state_filter: Literal["open", "resolved", "all"] = Query("open", alias="status"),
    severity: AlertSeverity | None = None,
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AlertListItem]:
    return alert_service.list_alerts(db, state=state_filter, severity=severity, limit=limit)


@router.patch("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN)),
) -> AlertRead:
    try:
        return AlertRead.model_validate(alert_service.resolve_alert(db, alert_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
