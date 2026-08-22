"""CRUD routes for robots."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.database import get_db
from app.models import UserRole
from app.schemas.robot import RobotCreate, RobotOperationalStatusUpdate, RobotRead, RobotUpdate
from app.services import robot_service
from app.services.exceptions import ConflictError, InvalidReferenceError, NotFoundError


router = APIRouter(prefix="/api/v1/robots", tags=["robots"])
admin_write = Depends(require_roles(UserRole.ADMIN))


@router.post("", response_model=RobotRead, status_code=status.HTTP_201_CREATED)
def create_robot(payload: RobotCreate, db: Session = Depends(get_db), _: object = admin_write) -> RobotRead:
    try:
        return robot_service.create_robot(db, payload)
    except InvalidReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{robot_id}/status", response_model=RobotRead)
def update_robot_status(
    robot_id: uuid.UUID,
    payload: RobotOperationalStatusUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(UserRole.OPERATOR, UserRole.ADMIN)),
) -> RobotRead:
    return robot_service.update_robot_status(db, robot_id, payload.status)


@router.get("", response_model=list[RobotRead])
def list_robots(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[RobotRead]:
    return robot_service.list_robots(db, skip=skip, limit=limit)


@router.get("/{robot_id}", response_model=RobotRead)
def get_robot(robot_id: uuid.UUID, db: Session = Depends(get_db)) -> RobotRead:
    try:
        return robot_service.get_robot(db, robot_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{robot_id}", response_model=RobotRead)
def update_robot(
    robot_id: uuid.UUID, payload: RobotUpdate, db: Session = Depends(get_db), _: object = admin_write
) -> RobotRead:
    try:
        return robot_service.update_robot(db, robot_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{robot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_robot(robot_id: uuid.UUID, db: Session = Depends(get_db), _: object = admin_write) -> None:
    try:
        robot_service.delete_robot(db, robot_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
