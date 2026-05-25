from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DDEP_", extra="ignore")

    app_name: str = "DDEP API"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://ddep:ddep@localhost:5432/ddep"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
