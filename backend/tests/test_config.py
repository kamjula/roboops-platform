import pytest
from pydantic import ValidationError

from app.core.config import Settings, normalize_database_url


JWT_SECRET = "test-jwt-secret-value-for-config-tests-123"


def test_settings_normalize_standard_postgresql_url_to_psycopg_driver(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_SECRET)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example/roboops")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://user:pass@db.example/roboops"


def test_settings_preserve_explicit_psycopg_driver_url(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_SECRET)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db.example/roboops")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://user:pass@db.example/roboops"


def test_normalize_database_url_supports_legacy_provider_scheme():
    assert normalize_database_url("postgres://user:pass@db.example/roboops?sslmode=require") == (
        "postgresql+psycopg://user:pass@db.example/roboops?sslmode=require"
    )


def test_rate_limit_settings_have_safe_bounds(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_SECRET)
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
