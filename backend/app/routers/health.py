from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, str]:
    """Liveness probe: the API process can accept and handle requests."""
    return {"status": "ok", "service": "roboops-backend"}


@router.get("/ready")
def readiness_check(response: Response, db: Session = Depends(get_db)) -> dict:
    """Readiness probe: the API can execute a query against PostgreSQL."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "checks": {"database": "unavailable"}}
    return {"status": "ready", "checks": {"database": "ok"}}
