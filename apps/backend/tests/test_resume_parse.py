from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.ai_client import AIClientError, _anthropic_response_text
from app.services.resume import convert_pdf_bytes_to_markdown, load_resume_pdf_to_md_module, process_resume_parse_job

from conftest import create_test_user


def test_settings_env_file_is_absolute() -> None:
    env_file = Path(Settings.model_config["env_file"])
    assert env_file.is_absolute()
    assert env_file.name == ".env"


def test_settings_prefers_minimax_over_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "RESUME_AI_API_KEY",
        "MATCH_AI_API_KEY",
        "MINIMAX_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "RESUME_AI_BASE_URL",
        "MATCH_AI_BASE_URL",
        "MINIMAX_BASE_URL",
        "ANTHROPIC_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")

    settings = Settings(
        _env_file=None,
        resume_ai_provider="minimax",
        match_ai_provider="minimax",
        interview_ai_provider="minimax",
        resume_ai_api_key=None,
        match_ai_api_key=None,
        interview_ai_api_key=None,
        resume_ai_base_url="",
        match_ai_base_url="",
        interview_ai_base_url="",
    )

    assert settings.resume_ai_api_key == "minimax-key"
    assert settings.match_ai_api_key == "minimax-key"
    assert settings.interview_ai_api_key == "minimax-key"
    assert settings.resume_ai_base_url == "https://api.minimaxi.com/anthropic"
    assert settings.match_ai_base_url == "https://api.minimaxi.com/anthropic"


def test_settings_defaults_to_codex2gpt_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "RESUME_AI_API_KEY",
        "MATCH_AI_API_KEY",
        "INTERVIEW_AI_API_KEY",
        "MINIMAX_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "RESUME_AI_BASE_URL",
        "MATCH_AI_BASE_URL",
        "INTERVIEW_AI_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.resume_ai_provider == "codex2gpt"
    assert settings.resume_ai_base_url == "http://127.0.0.1:18100/v1"
    assert settings.resume_ai_api_key is None
    assert settings.resume_ai_model == "gpt-5.4"
    assert settings.resume_pdf_ai_primary_timeout_seconds == 120
    assert settings.resume_pdf_ai_retry_count == 2
    assert settings.resume_pdf_ai_secondary_provider == ""
    assert settings.resume_pdf_ai_secondary_base_url == "http://127.0.0.1:11434"
    assert settings.resume_pdf_ai_secondary_api_key is None
    assert settings.resume_pdf_ai_secondary_model == "qwen2.5:7b"
    assert settings.resume_pdf_ai_secondary_timeout_seconds == 20
    assert settings.match_ai_provider == "codex2gpt"
    assert settings.match_ai_base_url == "http://127.0.0.1:18100/v1"
    assert settings.match_ai_api_key is None
    assert settings.match_ai_model == "gpt-5.4"
    assert settings.interview_ai_provider == "codex2gpt"
    assert settings.interview_ai_base_url == "http://127.0.0.1:18100/v1"
    assert settings.interview_ai_api_key is None
    assert settings.interview_ai_model == "gpt-5.4"


def test_settings_does_not_backfill_ollama_with_remote_provider_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "RESUME_AI_API_KEY",
        "MATCH_AI_API_KEY",
        "MINIMAX_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
        "RESUME_AI_BASE_URL",
        "MATCH_AI_BASE_URL",
        "MINIMAX_BASE_URL",
        "ANTHROPIC_BASE_URL",
        "INTERVIEW_AI_MODEL",
        "MATCH_AI_MODEL",
        "MINIMAX_MODEL_PLANNING",
        "MINIMAX_MODEL_REALTIME",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")

    settings = Settings(
        _env_file=None,
        resume_ai_provider="ollama",
        resume_ai_base_url="",
        resume_ai_api_key=None,
        resume_ai_model="qwen2.5:7b",
        interview_ai_provider="ollama",
        interview_ai_base_url="",
        interview_ai_api_key=None,
        interview_ai_model="qwen2.5:7b",
        interview_ai_model_planning="",
        interview_ai_model_realtime="",
        match_ai_provider="ollama",
        match_ai_base_url="",
        match_ai_api_key=None,
        match_ai_model="qwen2.5:7b",
    )

    assert settings.resume_ai_base_url == ""
    assert settings.resume_ai_api_key is None
    assert settings.match_ai_base_url == ""
    assert settings.match_ai_api_key is None
    assert settings.interview_ai_base_url == ""
    assert settings.interview_ai_api_key is None
    assert settings.interview_ai_model_planning == "qwen2.5:7b"
    assert settings.interview_ai_model_realtime == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_convert_pdf_bytes_to_markdown_returns_primary_ai_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_resume_pdf_to_md_module()

    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**kwargs) -> str:
        assert kwargs["retry_count_override"] == 2
        assert kwargs["total_timeout_budget_seconds"] == 120
        assert kwargs["config"].provider == "codex2gpt"
        assert kwargs["config"].timeout_seconds == 120
        assert kwargs["config"].read_timeout_seconds == settings.resume_ai_read_timeout_seconds
        return "# Polished"

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

    settings = Settings(_env_file=None)

    result = await convert_pdf_bytes_to_markdown(b"%PDF", "resume.pdf", settings=settings)

    assert result.markdown == "# Polished"
    assert result.raw_markdown == "# Raw"
    assert result.cleaned_markdown == "# Polished"
    assert result.ai_used is True
    assert result.ai_applied is True
    assert result.ai_provider == "codex2gpt"
    assert result.ai_model == "gpt-5.4"
    assert result.ai_error is None
    assert result.fallback_used is False
    assert result.prompt_version == "resume_pdf_to_md_v2"
    assert result.ai_latency_ms is not None
    assert result.ai_path == "primary"
    assert result.degraded_used is False
    assert result.ai_chain_latency_ms is not None
    assert len(result.ai_attempts) == 1
    assert result.ai_attempts[0].stage == "primary"
    assert result.ai_attempts[0].status == "success"
    assert result.configured_primary_provider == "codex2gpt"
    assert result.configured_primary_model == "gpt-5.4"
    assert result.configured_secondary_provider == ""
    assert result.configured_secondary_model == ""
    assert result.last_attempt_status == "success"
    assert result.ai_error_category is None


@pytest.mark.asyncio
async def test_convert_pdf_bytes_to_markdown_falls_back_after_primary_timeout_without_secondary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_resume_pdf_to_md_module()

    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    calls: list[str] = []

    async def fake_request_text_completion(**kwargs) -> str:
        calls.append(kwargs["config"].provider)
        assert kwargs["retry_count_override"] == 2
        assert kwargs["total_timeout_budget_seconds"] == 120
        raise AIClientError(category="timeout", detail="primary timeout")

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

    settings = Settings(_env_file=None, resume_pdf_ai_secondary_provider="ollama")

    result = await convert_pdf_bytes_to_markdown(b"%PDF", "resume.pdf", settings=settings)

    assert result.markdown == "# Raw"
    assert result.cleaned_markdown == "# Raw"
    assert result.ai_used is False
    assert result.ai_provider == ""
    assert result.ai_model == ""
    assert result.ai_applied is False
    assert result.fallback_used is True
    assert result.ai_path == "rules"
    assert result.degraded_used is True
    assert result.prompt_version == "resume_pdf_to_md_v2"
    assert result.ai_latency_ms is not None
    assert result.ai_chain_latency_ms is not None
    assert len(result.ai_attempts) == 1
    assert result.ai_attempts[0].status == "timeout"
    assert result.configured_secondary_provider == ""
    assert result.configured_secondary_model == ""
    assert result.last_attempt_status == "timeout"
    assert result.ai_error_category == "timeout"
    assert result.ai_error_message == "primary timeout"
    assert calls == ["codex2gpt"]


@pytest.mark.asyncio
async def test_convert_pdf_bytes_to_markdown_falls_back_on_primary_error_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_resume_pdf_to_md_module()

    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**kwargs) -> str:
        raise AIClientError(category="connection_error", detail="primary down")

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

    settings = Settings(_env_file=None, resume_pdf_ai_secondary_provider="ollama")

    result = await convert_pdf_bytes_to_markdown(b"%PDF", "resume.pdf", settings=settings)

    assert result.markdown == "# Raw"
    assert result.raw_markdown == "# Raw"
    assert result.cleaned_markdown == "# Raw"
    assert result.ai_used is False
    assert result.ai_applied is False
    assert result.ai_provider == ""
    assert result.ai_model == ""
    assert result.ai_error == "primary down"
    assert result.fallback_used is True
    assert result.ai_path == "rules"
    assert result.degraded_used is True
    assert result.prompt_version == "resume_pdf_to_md_v2"
    assert result.ai_latency_ms is not None
    assert result.ai_chain_latency_ms is not None
    assert len(result.ai_attempts) == 1
    assert result.ai_attempts[0].status == "connection_error"
    assert result.configured_primary_provider == "codex2gpt"
    assert result.configured_secondary_provider == ""
    assert result.configured_secondary_model == ""
    assert result.last_attempt_status == "connection_error"
    assert result.ai_error_category == "connection_error"
    assert result.ai_error_message == "primary down"


@pytest.mark.asyncio
async def test_convert_pdf_bytes_to_markdown_accepts_ai_markdown_when_quality_guard_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_resume_pdf_to_md_module()

    monkeypatch.setattr(
        module,
        "extract_raw_markdown_from_pdf",
        lambda *_args, **_kwargs: "# 张三\n\n- 邮箱：foo@example.com\n\n## 教育经历\n- Example University\n",
    )

    async def fake_request_text_completion(**kwargs) -> str:
        return "# 张三\n\n## 教育经历\n- Example University\n"

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

    settings = Settings(_env_file=None, resume_pdf_ai_secondary_provider="ollama")
    result = await convert_pdf_bytes_to_markdown(b"%PDF", "resume.pdf", settings=settings)

    assert result.ai_used is True
    assert result.ai_path == "primary"
    assert result.degraded_used is False
    assert result.fallback_used is False
    assert len(result.ai_attempts) == 1
    assert result.ai_attempts[0].status == "success"
    assert result.ai_attempts[0].error == "AI output removed email(s): foo@example.com"
    assert result.ai_error == "AI output removed email(s): foo@example.com"
    assert result.ai_error_category == "quality_guard_failed"
    assert result.last_attempt_status == "success"


@pytest.mark.asyncio
async def test_pdf_to_md_endpoint_returns_raw_markdown_when_ai_fails(
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user, token = await create_test_user(db_session, email="pdf-to-md@example.com")
    del user

    module = load_resume_pdf_to_md_module()
    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**_kwargs) -> str:
        raise AIClientError(category="connection_error", detail="network down")

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)
    caplog.set_level(logging.INFO)

    response = await client.post(
        "/tailored-resumes/pdf-to-md",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["markdown"] == "# Raw"
    assert payload["raw_markdown"] == "# Raw"
    assert payload["cleaned_markdown"] == "# Raw"
    assert payload["ai_used"] is False
    assert payload["ai_provider"] == ""
    assert payload["ai_model"] == ""
    assert payload["ai_error"] == "network down"
    assert payload["fallback_used"] is True
    assert payload["prompt_version"] == "resume_pdf_to_md_v2"
    assert payload["ai_latency_ms"] is not None
    assert payload["ai_path"] == "rules"
    assert payload["degraded_used"] is True
    assert payload["ai_chain_latency_ms"] is not None
    assert len(payload["ai_attempts"]) == 1
    assert payload["ai_attempts"][0]["stage"] == "primary"
    assert payload["configured_primary_provider"] == "codex2gpt"
    assert payload["configured_primary_model"] == "gpt-5.4"
    assert payload["configured_secondary_provider"] == ""
    assert payload["configured_secondary_model"] == ""
    assert payload["last_attempt_status"] == "connection_error"
    assert "resume_id=None parse_job_id=None ai_used=False ai_error=network down" in caplog.text
    assert "fallback_used=True prompt_version=resume_pdf_to_md_v2" in caplog.text
    assert "ai_path=rules degraded_used=True" in caplog.text


@pytest.mark.asyncio
async def test_resume_parse_job_succeeds_with_raw_markdown_fallback(
    app,
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user, token = await create_test_user(db_session, email="resume-parse@example.com")
    del user

    module = load_resume_pdf_to_md_module()
    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**_kwargs) -> str:
        raise AIClientError(category="connection_error", detail="network down")

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)
    caplog.set_level(logging.INFO)

    upload_response = await client.post(
        "/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 201

    upload_payload = upload_response.json()["data"]
    resume_id = UUID(upload_payload["id"])
    parse_job_id = UUID(upload_payload["latest_parse_job"]["id"])

    await process_resume_parse_job(
        resume_id=resume_id,
        parse_job_id=parse_job_id,
        storage=app.state.object_storage,
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    detail_response = await client.get(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    payload = detail_response.json()["data"]

    assert payload["parse_status"] == "success"
    assert payload["parse_error"] is None
    assert payload["raw_text"] == "# Raw"
    assert payload["parse_artifacts_json"]["raw_resume_md"] == "# Raw"
    assert payload["parse_artifacts_json"]["canonical_resume_md"] == "# Raw"
    assert payload["parse_artifacts_json"]["ai_used"] is False
    assert payload["parse_artifacts_json"]["ai_provider"] == ""
    assert payload["parse_artifacts_json"]["ai_model"] == ""
    assert payload["parse_artifacts_json"]["ai_error"] == "network down"
    assert payload["parse_artifacts_json"]["fallback_used"] is True
    assert payload["parse_artifacts_json"]["prompt_version"] == "resume_pdf_to_md_v2"
    assert payload["parse_artifacts_json"]["ai_latency_ms"] is not None
    assert payload["parse_artifacts_json"]["ai_path"] == "rules"
    assert payload["parse_artifacts_json"]["degraded_used"] is True
    assert payload["parse_artifacts_json"]["ai_chain_latency_ms"] is not None
    assert len(payload["parse_artifacts_json"]["ai_attempts"]) == 1
    assert payload["parse_artifacts_json"]["configured_primary_provider"] == "codex2gpt"
    assert payload["parse_artifacts_json"]["configured_primary_model"] == "gpt-5.4"
    assert payload["parse_artifacts_json"]["configured_secondary_provider"] == ""
    assert payload["parse_artifacts_json"]["configured_secondary_model"] == ""
    assert payload["parse_artifacts_json"]["last_attempt_status"] == "connection_error"
    assert payload["parse_artifacts_json"]["meta"]["ai_correction_applied"] is False
    assert payload["parse_artifacts_json"]["meta"]["ai_fallback_used"] is True
    assert payload["parse_artifacts_json"]["meta"]["ai_error_category"] == "connection_error"
    assert payload["latest_parse_job"]["status"] == "success"
    assert payload["latest_parse_job"]["ai_status"] == "fallback"
    assert "回退原始 Markdown" in payload["latest_parse_job"]["ai_message"]
    assert f"resume_id={resume_id} parse_job_id={parse_job_id} ai_used=False ai_error=network down" in caplog.text
    assert "markdown_length_before=5 markdown_length_after=5 fallback_used=True" in caplog.text
    assert "ai_path=rules degraded_used=True" in caplog.text


@pytest.mark.asyncio
async def test_resume_parse_job_persists_ai_cleanup_metadata_on_success(
    app,
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, token = await create_test_user(db_session, email="resume-parse-success@example.com")

    module = load_resume_pdf_to_md_module()
    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**_kwargs) -> str:
        return "# Cleaned"

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)
    caplog.set_level(logging.INFO)

    upload_response = await client.post(
        "/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 201

    upload_payload = upload_response.json()["data"]
    resume_id = UUID(upload_payload["id"])
    parse_job_id = UUID(upload_payload["latest_parse_job"]["id"])

    await process_resume_parse_job(
        resume_id=resume_id,
        parse_job_id=parse_job_id,
        storage=app.state.object_storage,
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    detail_response = await client.get(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    payload = detail_response.json()["data"]

    assert payload["parse_artifacts_json"]["raw_resume_md"] == "# Raw"
    assert payload["parse_artifacts_json"]["canonical_resume_md"] == "# Cleaned"
    assert payload["parse_artifacts_json"]["ai_used"] is True
    assert payload["parse_artifacts_json"]["ai_provider"] == "codex2gpt"
    assert payload["parse_artifacts_json"]["ai_model"] == "gpt-5.4"
    assert payload["parse_artifacts_json"]["ai_error"] is None
    assert payload["parse_artifacts_json"]["fallback_used"] is False
    assert payload["parse_artifacts_json"]["prompt_version"] == "resume_pdf_to_md_v2"
    assert payload["parse_artifacts_json"]["ai_latency_ms"] is not None
    assert payload["parse_artifacts_json"]["ai_path"] == "primary"
    assert payload["parse_artifacts_json"]["degraded_used"] is False
    assert payload["parse_artifacts_json"]["ai_chain_latency_ms"] is not None
    assert len(payload["parse_artifacts_json"]["ai_attempts"]) == 1
    assert payload["parse_artifacts_json"]["configured_primary_provider"] == "codex2gpt"
    assert payload["parse_artifacts_json"]["configured_primary_model"] == "gpt-5.4"
    assert payload["parse_artifacts_json"]["configured_secondary_provider"] == ""
    assert payload["parse_artifacts_json"]["configured_secondary_model"] == ""
    assert payload["parse_artifacts_json"]["last_attempt_status"] == "success"
    assert payload["latest_parse_job"]["ai_status"] == "applied"
    assert f"resume_id={resume_id} parse_job_id={parse_job_id} ai_used=True ai_error=None" in caplog.text
    assert "markdown_length_before=5 markdown_length_after=9 fallback_used=False" in caplog.text
    assert "ai_path=primary degraded_used=False" in caplog.text


@pytest.mark.asyncio
async def test_resume_parse_job_accepts_ai_markdown_when_quality_guard_warns(
    app,
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, token = await create_test_user(db_session, email="resume-parse-quality-warning@example.com")

    module = load_resume_pdf_to_md_module()
    monkeypatch.setattr(
        module,
        "extract_raw_markdown_from_pdf",
        lambda *_args, **_kwargs: "# 张三\n\n- 邮箱：foo@example.com\n\n## 教育经历\n- Example University\n",
    )

    async def fake_request_text_completion(**_kwargs) -> str:
        return "# 张三\n\n## 教育经历\n- Example University\n"

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)
    caplog.set_level(logging.INFO)

    upload_response = await client.post(
        "/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 201

    upload_payload = upload_response.json()["data"]
    resume_id = UUID(upload_payload["id"])
    parse_job_id = UUID(upload_payload["latest_parse_job"]["id"])

    await process_resume_parse_job(
        resume_id=resume_id,
        parse_job_id=parse_job_id,
        storage=app.state.object_storage,
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    detail_response = await client.get(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    payload = detail_response.json()["data"]

    assert payload["parse_artifacts_json"]["canonical_resume_md"] == "# 张三\n\n## 教育经历\n- Example University"
    assert payload["parse_artifacts_json"]["ai_used"] is True
    assert payload["parse_artifacts_json"]["fallback_used"] is False
    assert payload["parse_artifacts_json"]["ai_error"] == "AI output removed email(s): foo@example.com"
    assert payload["parse_artifacts_json"]["ai_error_category"] == "quality_guard_failed"
    assert payload["parse_artifacts_json"]["last_attempt_status"] == "success"
    assert payload["parse_artifacts_json"]["ai_attempts"][0]["status"] == "success"
    assert payload["parse_artifacts_json"]["ai_attempts"][0]["error"] == "AI output removed email(s): foo@example.com"
    assert payload["latest_parse_job"]["ai_status"] == "applied"
    assert "质量守卫仅记录告警，不再阻断" in (payload["latest_parse_job"]["ai_message"] or "")
    assert "ai_used=True ai_error=AI output removed email(s): foo@example.com" in caplog.text


@pytest.mark.asyncio
async def test_pdf_to_md_endpoint_still_fails_when_raw_markdown_is_empty(
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, token = await create_test_user(db_session, email="pdf-empty@example.com")
    del user

    module = load_resume_pdf_to_md_module()
    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "")

    response = await client.post(
        "/tailored-resumes/pdf-to-md",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "PDF 转 Markdown 失败，未生成可用内容"


@pytest.mark.asyncio
async def test_retry_resume_parse_endpoint_creates_new_parse_job_and_schedules_it(
    app,
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, token = await create_test_user(db_session, email="resume-retry@example.com")

    scheduled: dict[str, str] = {}

    def fake_schedule_resume_parse_job(app_obj, *, resume_id, parse_job_id, storage) -> None:
        del app_obj, storage
        scheduled["resume_id"] = str(resume_id)
        scheduled["parse_job_id"] = str(parse_job_id)

    monkeypatch.setattr(
        "app.routers.resumes.schedule_resume_parse_job",
        fake_schedule_resume_parse_job,
    )

    upload_response = await client.post(
        "/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 201

    payload = upload_response.json()["data"]
    resume_id = payload["id"]
    first_parse_job_id = payload["latest_parse_job"]["id"]

    retry_response = await client.post(
        f"/resumes/{resume_id}/parse",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retry_response.status_code == 200

    retry_payload = retry_response.json()["data"]
    assert retry_payload["id"] == resume_id
    assert retry_payload["parse_status"] == "pending"
    assert retry_payload["latest_parse_job"]["id"] != first_parse_job_id
    assert retry_payload["latest_parse_job"]["status"] == "pending"
    assert scheduled["resume_id"] == resume_id
    assert scheduled["parse_job_id"] == retry_payload["latest_parse_job"]["id"]


@pytest.mark.asyncio
async def test_save_resume_structured_data_normalizes_noncanonical_markdown(
    client,
    db_session,
    pdf_bytes: bytes,
) -> None:
    _, token = await create_test_user(db_session, email="resume-save@example.com")

    upload_response = await client.post(
        "/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 201
    resume_id = upload_response.json()["data"]["id"]

    response = await client.put(
        f"/resumes/{resume_id}/structured",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "markdown": "\n".join(
                [
                    "张三",
                    "教育背景",
                    "新疆大学（211 / 双一流）",
                    "本科 / 软件工程 | 2023.09 – 2027.06 | GPA 3.73，专业排名 50/800",
                    "",
                    "**竞赛获奖：** 百度之星省赛金奖；RoboCup 新疆一等奖",
                    "**科研成果：** 发表 RV-DANet 相关论文",
                ]
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["parse_status"] == "success"
    assert payload["structured_json"]["basic_info"]["name"] == "张三"
    assert payload["structured_json"]["education_items"][0]["school"] == "新疆大学（211 / 双一流）"
    assert payload["parse_artifacts_json"]["canonical_resume_md"].startswith("# 张三")
    assert "## 教育背景" in payload["parse_artifacts_json"]["canonical_resume_md"]
    assert "### 新疆大学（211 / 双一流）" in payload["parse_artifacts_json"]["canonical_resume_md"]


def test_anthropic_response_text_reports_stop_reason_for_thinking_only() -> None:
    class ThinkingBlock:
        type = "thinking"
        thinking = "..."

    class Response:
        content = [ThinkingBlock()]
        stop_reason = "max_tokens"

    with pytest.raises(ValueError, match="stop_reason=max_tokens"):
        _anthropic_response_text(Response())
