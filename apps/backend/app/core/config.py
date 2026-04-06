from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import SplitResult, urlsplit, urlunsplit

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.services.resume_ai import normalize_ai_provider, provider_requires_api_key

BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


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


DEFAULT_CODEX2GPT_BASE_URL = "http://127.0.0.1:18100/v1"
DEFAULT_CODEX2GPT_MODEL = "gpt-5.4"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"


def _first_non_empty_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


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
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
    )
    match_ai_provider: str = "codex2gpt"
    match_ai_base_url: str | None = DEFAULT_CODEX2GPT_BASE_URL
    match_ai_api_key: str | None = None
    match_ai_model: str | None = DEFAULT_CODEX2GPT_MODEL
    match_ai_timeout_seconds: int = 90
    resume_ai_provider: str = "codex2gpt"
    resume_ai_base_url: str = DEFAULT_CODEX2GPT_BASE_URL
    resume_ai_api_key: str | None = None
    resume_ai_model: str = DEFAULT_CODEX2GPT_MODEL
    resume_ai_timeout_seconds: int = 30
    resume_pdf_ai_primary_timeout_seconds: int = 30
    resume_pdf_ai_retry_count: int = 0
    resume_pdf_ai_secondary_provider: str = "ollama"
    resume_pdf_ai_secondary_base_url: str = DEFAULT_OLLAMA_BASE_URL
    resume_pdf_ai_secondary_api_key: str | None = None
    resume_pdf_ai_secondary_model: str = DEFAULT_OLLAMA_MODEL
    resume_pdf_ai_secondary_timeout_seconds: int = 20
    interview_ai_provider: str = "codex2gpt"
    interview_ai_base_url: str = DEFAULT_CODEX2GPT_BASE_URL
    interview_ai_api_key: str | None = None
    interview_ai_model: str = DEFAULT_CODEX2GPT_MODEL
    interview_ai_model_planning: str | None = None
    interview_ai_model_realtime: str | None = None
    interview_ai_timeout_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE),
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
        "resume_pdf_ai_secondary_base_url",
        "interview_ai_base_url",
        mode="before",
    )
    @classmethod
    def resolve_ai_base_url(cls, value: str | None, info: ValidationInfo) -> str | None:
        provider_field = info.field_name.replace("_base_url", "_provider")
        provider = normalize_ai_provider(info.data.get(provider_field))
        if value is None or not str(value).strip():
            if provider == "ollama":
                return value
            if provider == "codex2gpt":
                return DEFAULT_CODEX2GPT_BASE_URL
            value = _first_non_empty_env("MINIMAX_BASE_URL", "ANTHROPIC_BASE_URL")
        return _normalize_ai_base_url(value)

    @field_validator("match_ai_api_key", mode="before")
    @classmethod
    def resolve_match_ai_api_key(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None and value.strip():
            return value
        if not provider_requires_api_key(info.data.get("match_ai_provider")):
            return value
        return _first_non_empty_env(
            "MINIMAX_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
        )

    @field_validator("resume_ai_api_key", mode="before")
    @classmethod
    def resolve_resume_ai_api_key(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None and value.strip():
            return value
        if not provider_requires_api_key(info.data.get("resume_ai_provider")):
            return value
        return _first_non_empty_env(
            "MINIMAX_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
        )

    @field_validator("resume_pdf_ai_secondary_api_key", mode="before")
    @classmethod
    def resolve_resume_pdf_ai_secondary_api_key(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        if value is not None and value.strip():
            return value
        if not provider_requires_api_key(info.data.get("resume_pdf_ai_secondary_provider")):
            return value
        return _first_non_empty_env(
            "MINIMAX_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
        )

    @field_validator("interview_ai_api_key", mode="before")
    @classmethod
    def resolve_interview_ai_api_key(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None and value.strip():
            return value
        if not provider_requires_api_key(info.data.get("interview_ai_provider")):
            return value
        return _first_non_empty_env(
            "MATCH_AI_API_KEY",
            "MINIMAX_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY",
        )

    @field_validator("interview_ai_model_planning", mode="before")
    @classmethod
    def resolve_interview_ai_model_planning(cls, value: str | None) -> str | None:
        if value is not None and value.strip():
            return value
        return _first_non_empty_env("INTERVIEW_AI_MODEL", "MATCH_AI_MODEL", "MINIMAX_MODEL_PLANNING")

    @field_validator("interview_ai_model_realtime", mode="before")
    @classmethod
    def resolve_interview_ai_model_realtime(cls, value: str | None) -> str | None:
        if value is not None and value.strip():
            return value
        return _first_non_empty_env("INTERVIEW_AI_MODEL", "MINIMAX_MODEL_REALTIME")

    @model_validator(mode="after")
    def resolve_match_ai_fallbacks(self) -> "Settings":
        match_provider = normalize_ai_provider(self.match_ai_provider)
        interview_provider = normalize_ai_provider(self.interview_ai_provider)
        if match_provider == "":
            self.match_ai_provider = (self.resume_ai_provider or "codex2gpt").strip()
            match_provider = normalize_ai_provider(self.match_ai_provider)

        if match_provider == "codex2gpt" and not (self.match_ai_base_url or "").strip():
            self.match_ai_base_url = DEFAULT_CODEX2GPT_BASE_URL
        elif match_provider != "ollama" and not (self.match_ai_base_url or "").strip():
            self.match_ai_base_url = self.resume_ai_base_url

        if not (self.match_ai_model or "").strip():
            self.match_ai_model = self.resume_ai_model

        if provider_requires_api_key(match_provider) and not (self.match_ai_api_key or "").strip():
            fallback_key = (self.resume_ai_api_key or "").strip() or (
                _first_non_empty_env(
                    "MINIMAX_API_KEY",
                    "ANTHROPIC_AUTH_TOKEN",
                    "ANTHROPIC_API_KEY",
                )
                or ""
            )
            self.match_ai_api_key = fallback_key or None

        if interview_provider == "codex2gpt" and not (self.interview_ai_base_url or "").strip():
            self.interview_ai_base_url = DEFAULT_CODEX2GPT_BASE_URL
        elif interview_provider != "ollama" and not (self.interview_ai_base_url or "").strip():
            fallback_base_url = (self.match_ai_base_url or "").strip() or (
                _first_non_empty_env("MINIMAX_BASE_URL", "ANTHROPIC_BASE_URL") or ""
            )
            self.interview_ai_base_url = fallback_base_url or self.resume_ai_base_url

        if provider_requires_api_key(interview_provider) and not (self.interview_ai_api_key or "").strip():
            fallback_key = (self.match_ai_api_key or "").strip() or (
                _first_non_empty_env(
                    "MINIMAX_API_KEY",
                    "ANTHROPIC_AUTH_TOKEN",
                    "ANTHROPIC_API_KEY",
                )
                or ""
            )
            self.interview_ai_api_key = fallback_key or None

        if not (self.interview_ai_model_planning or "").strip():
            fallback_model = (self.interview_ai_model or "").strip() or (
                _first_non_empty_env("INTERVIEW_AI_MODEL") or ""
            ) or (self.match_ai_model or "").strip() or (
                _first_non_empty_env("MINIMAX_MODEL_PLANNING") or ""
            )
            self.interview_ai_model_planning = fallback_model or self.interview_ai_model

        if not (self.interview_ai_model_realtime or "").strip():
            fallback_model = (
                (self.interview_ai_model or "").strip()
                or (_first_non_empty_env("INTERVIEW_AI_MODEL", "MINIMAX_MODEL_REALTIME") or "")
            )
            self.interview_ai_model_realtime = fallback_model or self.interview_ai_model

        explicit_interview_timeout = (
            _first_non_empty_env("INTERVIEW_AI_TIMEOUT_SECONDS") or ""
        )
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
