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
