from __future__ import annotations

from types import SimpleNamespace

from app.api.deps import get_settings_dependency
from app.core.config import Settings


def test_settings_include_resume_upload_fields() -> None:
    settings = Settings()

    assert settings.storage_provider == "minio"
    assert settings.storage_bucket_name == "career-pilot-resumes"
    assert settings.storage_presigned_expire_seconds == 3600
    assert settings.max_resume_file_size_mb == 10


def test_settings_dependency_prefers_app_state_settings() -> None:
    custom_settings = Settings(
        storage_bucket_name="custom-bucket",
        max_resume_file_size_mb=25,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=custom_settings),
        )
    )

    assert get_settings_dependency(request) is custom_settings


def test_settings_normalize_localhost_service_hosts() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://career:career@localhost:5432/career_pilot",
        alembic_database_url="postgresql+psycopg://career:career@localhost:5432/career_pilot",
        redis_url="redis://localhost:6380/0",
        storage_endpoint="localhost:9000",
    )

    assert settings.database_url == "postgresql+asyncpg://career:career@127.0.0.1:5432/career_pilot"
    assert (
        settings.alembic_database_url
        == "postgresql+psycopg://career:career@127.0.0.1:5432/career_pilot"
    )
    assert settings.redis_url == "redis://127.0.0.1:6380/0"
    assert settings.storage_endpoint == "127.0.0.1:9000"
