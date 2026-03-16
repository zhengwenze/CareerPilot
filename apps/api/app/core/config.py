from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from urllib.parse import SplitResult, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _normalize_localhost_url(value: str | None) -> str | None:
    if not value:
        return value

    parsed = urlsplit(value)
    if parsed.hostname != "localhost":
        return value

    netloc = parsed.netloc.replace("localhost", "127.0.0.1", 1)
    normalized = SplitResult(
        scheme=parsed.scheme,
        netloc=netloc,
        path=parsed.path,
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunsplit(normalized)


def _normalize_localhost_endpoint(value: str) -> str:
    if value == "localhost":
        return "127.0.0.1"
    if value.startswith("localhost:"):
        return value.replace("localhost:", "127.0.0.1:", 1)
    return value


class Settings(BaseSettings):
    app_name: str = "career-pilot-api"
    app_version: str = "0.1.0"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://career:career@localhost:5432/career_pilot"
    alembic_database_url: str | None = (
        "postgresql+psycopg://career:career@localhost:5432/career_pilot"
    )
    redis_url: str | None = "redis://localhost:6380/0"
    storage_provider: str = "minio"
    storage_endpoint: str = "localhost:9000"
    storage_access_key: str = "careerpilot"
    storage_secret_key: str = "careerpilot123"
    storage_bucket_name: str = "career-pilot-resumes"
    storage_use_ssl: bool = False
    storage_presigned_expire_seconds: int = 3600
    max_resume_file_size_mb: int = 10
    jwt_secret_key: str = Field(
        default="replace-this-with-a-very-long-dev-secret-key",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    match_ai_provider: str = "disabled"
    match_ai_base_url: str | None = None
    match_ai_api_key: str | None = None
    match_ai_model: str | None = None
    match_ai_timeout_seconds: int = 30

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

    @field_validator("database_url", "alembic_database_url", "redis_url", mode="before")
    @classmethod
    def normalize_localhost_urls(cls, value: str | None) -> str | None:
        return _normalize_localhost_url(value)

    @field_validator("storage_endpoint", mode="before")
    @classmethod
    def normalize_storage_endpoint(cls, value: str) -> str:
        return _normalize_localhost_endpoint(value)

    @property
    def sync_database_url(self) -> str:
        if self.alembic_database_url:
            return self.alembic_database_url
        return self.database_url.replace("+asyncpg", "+psycopg", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
