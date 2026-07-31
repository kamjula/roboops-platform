"""CRUD routes for sites."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.site import SiteCreate, SiteRead, SiteUpdate
from app.services import site_service
from app.services.exceptions import ConflictError, NotFoundError


router = APIRouter(prefix="/api/v1/sites", tags=["sites"])


@router.post("", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate, db: Session = Depends(get_db)) -> SiteRead:
    try:
        return site_service.create_site(db, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[SiteRead])
def list_sites(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[SiteRead]:
    return site_service.list_sites(db, skip=skip, limit=limit)


@router.get("/{site_id}", response_model=SiteRead)
def get_site(site_id: uuid.UUID, db: Session = Depends(get_db)) -> SiteRead:
    try:
        return site_service.get_site(db, site_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{site_id}", response_model=SiteRead)
def update_site(site_id: uuid.UUID, payload: SiteUpdate, db: Session = Depends(get_db)) -> SiteRead:
    try:
        return site_service.update_site(db, site_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    try:
        site_service.delete_site(db, site_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
