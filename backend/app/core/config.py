from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    environment: str = "development"
    database_url: str = "postgresql+psycopg://roboops_user:roboops_pass@localhost:5432/roboops_db"
    cors_origins: str = "http://localhost:5173"
    @property
    def cors_origin_list(self):
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

@lru_cache
def get_settings():
    return Settings()
