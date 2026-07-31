"""Service-layer CRUD operations for Site."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.robot import Robot
from app.models.site import Site
from app.schemas.site import SiteCreate, SiteUpdate
from app.services.exceptions import ConflictError, NotFoundError


def list_sites(db: Session, skip: int = 0, limit: int = 100) -> list[Site]:
    stmt = select(Site).order_by(Site.site_code.asc(), Site.id.asc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_site(db: Session, site_id: uuid.UUID) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise NotFoundError(f"Site {site_id} not found")
    return site


def create_site(db: Session, payload: SiteCreate) -> Site:
    site = Site(**payload.model_dump())
    db.add(site)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"Site with site_code '{payload.site_code}' already exists") from exc
    db.refresh(site)
    return site


def update_site(db: Session, site_id: uuid.UUID, payload: SiteUpdate) -> Site:
    site = get_site(db, site_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(site, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Site update violates a unique constraint") from exc
    db.refresh(site)
    return site


def delete_site(db: Session, site_id: uuid.UUID) -> None:
    site = get_site(db, site_id)
    has_robots = db.execute(select(Robot.id).where(Robot.site_id == site_id).limit(1)).first()
    if has_robots is not None:
        raise ConflictError("Cannot delete site: one or more robots reference this site")
    db.delete(site)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Cannot delete site due to related records") from exc
