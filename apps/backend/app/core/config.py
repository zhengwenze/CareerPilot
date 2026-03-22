from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated
from urllib.parse import SplitResult, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
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


def _normalize_ai_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return normalized
    return normalized.replace("api.minimax.io", "api.minimaxi.com")


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
    match_ai_provider: str = "minimax"
    match_ai_base_url: str | None = "https://api.minimaxi.com/anthropic"
    match_ai_api_key: str | None = None
    match_ai_model: str | None = "MiniMax-M2.5"
    match_ai_timeout_seconds: int = 90
    resume_ai_provider: str = "minimax"
    resume_ai_base_url: str = "https://api.minimaxi.com/anthropic"
    resume_ai_api_key: str | None = None
    resume_ai_model: str = "MiniMax-M2.5"
    resume_ai_timeout_seconds: int = 30
    interview_ai_provider: str = "minimax"
    interview_ai_base_url: str = "https://api.minimaxi.com/anthropic"
    interview_ai_api_key: str | None = None
    interview_ai_model: str = "MiniMax-M2.5"
    interview_ai_model_planning: str | None = None
    interview_ai_model_realtime: str | None = None
    interview_ai_timeout_seconds: int = 60

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

    @field_validator(
        "match_ai_base_url",
        "resume_ai_base_url",
        "interview_ai_base_url",
        mode="before",
    )
    @classmethod
    def resolve_ai_base_url(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            value = os.getenv("ANTHROPIC_BASE_URL")
        return _normalize_ai_base_url(value)

    @field_validator("match_ai_api_key", mode="before")
    @classmethod
    def resolve_match_ai_api_key(cls, value: str | None) -> str | None:
        if value is not None and value.strip():
            return value
        anthropic_auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()
        if anthropic_auth_token:
            return anthropic_auth_token
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return anthropic_api_key or None

    @field_validator("resume_ai_api_key", mode="before")
    @classmethod
    def resolve_resume_ai_api_key(cls, value: str | None) -> str | None:
        if value is not None and value.strip():
            return value
        anthropic_auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()
        if anthropic_auth_token:
            return anthropic_auth_token
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return anthropic_api_key or None

    @field_validator("interview_ai_api_key", mode="before")
    @classmethod
    def resolve_interview_ai_api_key(cls, value: str | None) -> str | None:
        if value is not None and value.strip():
            return value
        match_ai_api_key = os.getenv("MATCH_AI_API_KEY", "").strip()
        if match_ai_api_key:
            return match_ai_api_key
        minimax_api_key = os.getenv("MINIMAX_API_KEY", "").strip()
        if minimax_api_key:
            return minimax_api_key
        anthropic_auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()
        if anthropic_auth_token:
            return anthropic_auth_token
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return anthropic_api_key or None

    @field_validator("interview_ai_model_planning", mode="before")
    @classmethod
    def resolve_interview_ai_model_planning(cls, value: str | None) -> str | None:
        if value is not None and value.strip():
            return value
        match_ai_model = os.getenv("MATCH_AI_MODEL", "").strip()
        if match_ai_model:
            return match_ai_model
        minimax_model_planning = os.getenv("MINIMAX_MODEL_PLANNING", "").strip()
        if minimax_model_planning:
            return minimax_model_planning
        return None

    @field_validator("interview_ai_model_realtime", mode="before")
    @classmethod
    def resolve_interview_ai_model_realtime(cls, value: str | None) -> str | None:
        if value is not None and value.strip():
            return value
        minimax_model_realtime = os.getenv("MINIMAX_MODEL_REALTIME", "").strip()
        if minimax_model_realtime:
            return minimax_model_realtime
        return None

    @model_validator(mode="after")
    def resolve_match_ai_fallbacks(self) -> "Settings":
        match_provider = (self.match_ai_provider or "").strip().lower()
        if match_provider == "":
            self.match_ai_provider = (self.resume_ai_provider or "minimax").strip()

        if not (self.match_ai_base_url or "").strip():
            self.match_ai_base_url = self.resume_ai_base_url

        if not (self.match_ai_model or "").strip():
            self.match_ai_model = self.resume_ai_model

        if not (self.match_ai_api_key or "").strip():
            fallback_key = (self.resume_ai_api_key or "").strip() or os.getenv(
                "ANTHROPIC_API_KEY", ""
            ).strip()
            self.match_ai_api_key = fallback_key or None

        if not (self.interview_ai_base_url or "").strip():
            fallback_base_url = (self.match_ai_base_url or "").strip() or os.getenv(
                "MINIMAX_BASE_URL", ""
            ).strip()
            self.interview_ai_base_url = fallback_base_url or self.resume_ai_base_url

        if not (self.interview_ai_api_key or "").strip():
            fallback_key = (self.match_ai_api_key or "").strip() or os.getenv(
                "MINIMAX_API_KEY", ""
            ).strip()
            self.interview_ai_api_key = fallback_key or None

        if not (self.interview_ai_model_planning or "").strip():
            fallback_model = (self.match_ai_model or "").strip() or os.getenv(
                "MINIMAX_MODEL_PLANNING", ""
            ).strip()
            self.interview_ai_model_planning = fallback_model or self.interview_ai_model

        if not (self.interview_ai_model_realtime or "").strip():
            fallback_model = os.getenv("MINIMAX_MODEL_REALTIME", "").strip()
            self.interview_ai_model_realtime = fallback_model or self.interview_ai_model

        explicit_interview_timeout = os.getenv("INTERVIEW_AI_TIMEOUT_SECONDS", "").strip()
        if not explicit_interview_timeout and self.interview_ai_timeout_seconds == 60:
            if self.match_ai_timeout_seconds and self.match_ai_timeout_seconds > 0:
                self.interview_ai_timeout_seconds = self.match_ai_timeout_seconds

        return self

    @property
    def sync_database_url(self) -> str:
        if self.alembic_database_url:
            return self.alembic_database_url
        return self.database_url.replace("+asyncpg", "+psycopg", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
