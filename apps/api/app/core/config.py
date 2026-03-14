from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "career-pilot-api"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://career:career@localhost:5432/career_pilot"
    alembic_database_url: str | None = "postgresql+psycopg://career:career@localhost:5432/career_pilot"
    redis_url: str | None = "redis://localhost:6380/0"
    jwt_secret_key: str = Field(
        default="replace-this-with-a-very-long-dev-secret-key",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def sync_database_url(self) -> str:
        if self.alembic_database_url:
            return self.alembic_database_url
        return self.database_url.replace("+asyncpg", "+psycopg", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
