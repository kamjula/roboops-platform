"""CRUD routes for robot models."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.robot_model import RobotModelCreate, RobotModelRead, RobotModelUpdate
from app.services import robot_model_service
from app.services.exceptions import ConflictError, NotFoundError


router = APIRouter(prefix="/api/v1/robot-models", tags=["robot-models"])


@router.post("", response_model=RobotModelRead, status_code=status.HTTP_201_CREATED)
def create_robot_model(payload: RobotModelCreate, db: Session = Depends(get_db)) -> RobotModelRead:
    try:
        return robot_model_service.create_robot_model(db, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[RobotModelRead])
def list_robot_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[RobotModelRead]:
    return robot_model_service.list_robot_models(db, skip=skip, limit=limit)


@router.get("/{robot_model_id}", response_model=RobotModelRead)
def get_robot_model(robot_model_id: uuid.UUID, db: Session = Depends(get_db)) -> RobotModelRead:
    try:
        return robot_model_service.get_robot_model(db, robot_model_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{robot_model_id}", response_model=RobotModelRead)
def update_robot_model(
    robot_model_id: uuid.UUID, payload: RobotModelUpdate, db: Session = Depends(get_db)
) -> RobotModelRead:
    try:
        return robot_model_service.update_robot_model(db, robot_model_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{robot_model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_robot_model(robot_model_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    try:
        robot_model_service.delete_robot_model(db, robot_model_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
