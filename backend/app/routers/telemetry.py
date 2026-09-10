"""Authenticated telemetry ingestion and query routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.database import get_db
from app.models import User, UserRole
from app.schemas.telemetry import TelemetryReadingCreate, TelemetryReadingResponse
from app.services import telemetry_service
from app.services.exceptions import ConflictError, IneligibleResourceError, NotFoundError

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])
operator_write = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN))
read_access = Depends(get_current_user)


def _response(reading) -> TelemetryReadingResponse:
    return TelemetryReadingResponse(
        id=reading.id,
        sensor_id=reading.sensor_id,
        robot_id=reading.robot_id,
        value=reading.value,
        observed_at=reading.recorded_at,
        source_event_id=reading.source_event_id,
        created_at=reading.created_at,
    )


def _normalize_filter(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{name} must include timezone information")
    return value.astimezone(timezone.utc)


@router.post("/readings", response_model=TelemetryReadingResponse, status_code=status.HTTP_201_CREATED)
def ingest_reading(
    payload: TelemetryReadingCreate,
    response: Response,
    db: Session = Depends(get_db),
    _: User = operator_write,
) -> TelemetryReadingResponse:
    try:
        result = telemetry_service.ingest_reading(db, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IneligibleResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return _response(result.reading)


@router.get("/robots/{robot_id}/latest", response_model=list[TelemetryReadingResponse], dependencies=[read_access])
def latest_robot_readings(robot_id: uuid.UUID, db: Session = Depends(get_db)) -> list[TelemetryReadingResponse]:
    try:
        readings = telemetry_service.get_latest_by_robot(db, robot_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_response(reading) for reading in readings]


@router.get("/sensors/{sensor_id}/readings", response_model=list[TelemetryReadingResponse], dependencies=[read_access])
def sensor_readings(
    sensor_id: uuid.UUID,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TelemetryReadingResponse]:
    start = _normalize_filter(start, "start")
    end = _normalize_filter(end, "end")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start must not be after end")
    try:
        readings = telemetry_service.get_sensor_readings(db, sensor_id, start=start, end=end, limit=limit)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [_response(reading) for reading in readings]