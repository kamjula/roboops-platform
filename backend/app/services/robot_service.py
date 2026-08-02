"""Service-layer CRUD operations for Robot."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.models.robot_model import RobotModel
from app.models.site import Site
from app.schemas.robot import RobotCreate, RobotUpdate
from app.services.exceptions import ConflictError, InvalidReferenceError, NotFoundError


def list_robots(db: Session, skip: int = 0, limit: int = 100) -> list[Robot]:
    stmt = select(Robot).order_by(Robot.robot_code.asc(), Robot.id.asc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_robot(db: Session, robot_id: uuid.UUID) -> Robot:
    robot = db.get(Robot, robot_id)
    if robot is None:
        raise NotFoundError(f"Robot {robot_id} not found")
    return robot


def _validate_site_exists(db: Session, site_id: uuid.UUID) -> None:
    if db.get(Site, site_id) is None:
        raise InvalidReferenceError(f"Site {site_id} does not exist")


def _validate_model_exists(db: Session, model_id: uuid.UUID) -> None:
    if db.get(RobotModel, model_id) is None:
        raise InvalidReferenceError(f"Robot model {model_id} does not exist")


def create_robot(db: Session, payload: RobotCreate) -> Robot:
    _validate_site_exists(db, payload.site_id)
    _validate_model_exists(db, payload.model_id)
    robot = Robot(**payload.model_dump())
    db.add(robot)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"Robot with robot_code '{payload.robot_code}' or serial_number "
            f"'{payload.serial_number}' already exists"
        ) from exc
    db.refresh(robot)
    return robot


def update_robot(db: Session, robot_id: uuid.UUID, payload: RobotUpdate) -> Robot:
    robot = get_robot(db, robot_id)
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("site_id") is not None:
        _validate_site_exists(db, updates["site_id"])
    if updates.get("model_id") is not None:
        _validate_model_exists(db, updates["model_id"])
    for field, value in updates.items():
        setattr(robot, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Robot with the given robot_code or serial_number already exists") from exc
    db.refresh(robot)
    return robot


def delete_robot(db: Session, robot_id: uuid.UUID) -> None:
    robot = get_robot(db, robot_id)
    db.delete(robot)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Cannot delete robot due to related records") from exc
