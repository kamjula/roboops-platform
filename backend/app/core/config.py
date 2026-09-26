from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(value: str) -> str:
    """Select psycopg v3 for provider-style PostgreSQL connection URLs."""
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    environment: str = "development"
    database_url: str = "postgresql+psycopg://roboops_user:roboops_pass@localhost:5432/roboops_db"
    cors_origins: str = "http://localhost:5173"
    jwt_secret_key: str = Field(..., min_length=32, description="JWT signing secret; must be provided via environment")
    jwt_algorithm: str = "HS256"
    access_token_expiry_minutes: int = 30
    login_rate_limit: int = Field(default=10, ge=1, le=10_000)
    telemetry_write_rate_limit: int = Field(default=120, ge=1, le=100_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    rate_limit_max_keys: int = Field(default=10_000, ge=100, le=1_000_000)
    roboops_public_demo_enabled: bool = False
    roboops_public_demo_email: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value):
        """Use the installed psycopg v3 driver for standard Postgres URLs."""
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @property
    def cors_origin_list(self):
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]


@lru_cache
def get_settings():
    return Settings()
