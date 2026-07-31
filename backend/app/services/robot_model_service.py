"""Service-layer CRUD operations for RobotModel."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.models.robot_model import RobotModel
from app.schemas.robot_model import RobotModelCreate, RobotModelUpdate
from app.services.exceptions import ConflictError, NotFoundError


def list_robot_models(db: Session, skip: int = 0, limit: int = 100) -> list[RobotModel]:
    stmt = (
        select(RobotModel).order_by(RobotModel.model_code.asc(), RobotModel.id.asc()).offset(skip).limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_robot_model(db: Session, robot_model_id: uuid.UUID) -> RobotModel:
    robot_model = db.get(RobotModel, robot_model_id)
    if robot_model is None:
        raise NotFoundError(f"RobotModel {robot_model_id} not found")
    return robot_model


def create_robot_model(db: Session, payload: RobotModelCreate) -> RobotModel:
    robot_model = RobotModel(**payload.model_dump())
    db.add(robot_model)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"RobotModel with model_code '{payload.model_code}' already exists") from exc
    db.refresh(robot_model)
    return robot_model


def update_robot_model(db: Session, robot_model_id: uuid.UUID, payload: RobotModelUpdate) -> RobotModel:
    robot_model = get_robot_model(db, robot_model_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(robot_model, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("RobotModel update violates a unique constraint") from exc
    db.refresh(robot_model)
    return robot_model


def delete_robot_model(db: Session, robot_model_id: uuid.UUID) -> None:
    robot_model = get_robot_model(db, robot_model_id)
    has_robots = db.execute(select(Robot.id).where(Robot.model_id == robot_model_id).limit(1)).first()
    if has_robots is not None:
        raise ConflictError("Cannot delete robot model: one or more robots reference this model")
    db.delete(robot_model)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Cannot delete robot model due to related records") from exc
