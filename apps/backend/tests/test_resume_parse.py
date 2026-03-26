from __future__ import annotations

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


@pytest.mark.asyncio
async def test_convert_pdf_bytes_to_markdown_returns_ai_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_resume_pdf_to_md_module()

    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**_kwargs) -> str:
        return "# Polished"

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

    settings = Settings(_env_file=None, resume_ai_api_key="key", resume_ai_base_url="https://api.minimaxi.com/anthropic")

    result = await convert_pdf_bytes_to_markdown(b"%PDF", "resume.pdf", settings=settings)

    assert result.markdown == "# Polished"
    assert result.raw_markdown == "# Raw"
    assert result.ai_applied is True
    assert result.fallback_used is False
    assert result.ai_error_category is None


@pytest.mark.asyncio
async def test_convert_pdf_bytes_to_markdown_falls_back_on_ai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_resume_pdf_to_md_module()

    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**_kwargs) -> str:
        raise AIClientError(category="connection_error", detail="network down")

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

    settings = Settings(_env_file=None, resume_ai_api_key="key", resume_ai_base_url="https://api.minimaxi.com/anthropic")

    result = await convert_pdf_bytes_to_markdown(b"%PDF", "resume.pdf", settings=settings)

    assert result.markdown == "# Raw"
    assert result.raw_markdown == "# Raw"
    assert result.ai_applied is False
    assert result.fallback_used is True
    assert result.ai_error_category == "connection_error"
    assert result.ai_error_message == "network down"


@pytest.mark.asyncio
async def test_pdf_to_md_endpoint_returns_raw_markdown_when_ai_fails(
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, token = await create_test_user(db_session, email="pdf-to-md@example.com")
    del user

    module = load_resume_pdf_to_md_module()
    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**_kwargs) -> str:
        raise AIClientError(category="connection_error", detail="network down")

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

    response = await client.post(
        "/tailored-resumes/pdf-to-md",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["markdown"] == "# Raw"


@pytest.mark.asyncio
async def test_resume_parse_job_succeeds_with_raw_markdown_fallback(
    app,
    client,
    db_session,
    pdf_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, token = await create_test_user(db_session, email="resume-parse@example.com")
    del user

    module = load_resume_pdf_to_md_module()
    monkeypatch.setattr(module, "extract_raw_markdown_from_pdf", lambda *_args, **_kwargs: "# Raw")

    async def fake_request_text_completion(**_kwargs) -> str:
        raise AIClientError(category="connection_error", detail="network down")

    monkeypatch.setattr(module, "request_text_completion", fake_request_text_completion)

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
    assert payload["parse_artifacts_json"]["canonical_resume_md"] == "# Raw"
    assert payload["parse_artifacts_json"]["meta"]["ai_correction_applied"] is False
    assert payload["parse_artifacts_json"]["meta"]["ai_fallback_used"] is True
    assert payload["parse_artifacts_json"]["meta"]["ai_error_category"] == "connection_error"
    assert payload["latest_parse_job"]["status"] == "success"
    assert payload["latest_parse_job"]["ai_status"] == "fallback"
    assert "回退原始 Markdown" in payload["latest_parse_job"]["ai_message"]


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
