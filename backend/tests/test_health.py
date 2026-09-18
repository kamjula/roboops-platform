from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "roboops-backend"}


def test_readiness_returns_generic_503_when_database_is_unavailable():
    class UnavailableDatabase:
        def execute(self, _statement):
            raise SQLAlchemyError("simulated connection failure with private details")

    def override_get_db():
        yield UnavailableDatabase()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable"},
    }
    assert "private details" not in response.text
