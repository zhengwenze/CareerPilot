from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.models import User
from app.routers.deps import get_current_user
from app.schemas.tailored_resume import TailoredResumePolishResponse
from app.services.tailored_resume_polish import polish_tailored_resume_markdown


@pytest.mark.asyncio
async def test_polish_tailored_resume_markdown_returns_markdown_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_text_completion(**_: object) -> str:
        return "# 郑文泽\n\n- 主导增长分析项目，推动关键指标提升。"

    monkeypatch.setattr(
        "app.services.tailored_resume_polish.request_text_completion",
        fake_request_text_completion,
    )

    response = await polish_tailored_resume_markdown(
        text="# 郑文泽\n\n- 做增长分析",
        settings=Settings(
            resume_ai_provider="minimax",
            resume_ai_base_url="https://api.minimaxi.com/anthropic",
            resume_ai_api_key="test-key",
            resume_ai_model="MiniMax-M2.5",
        ),
    )

    assert isinstance(response, TailoredResumePolishResponse)
    assert response.text.startswith("# 郑文泽")
    assert "主导增长分析项目" in response.text


@pytest.mark.asyncio
async def test_tailored_resume_polish_api_returns_success_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_polish_tailored_resume_markdown(**_: object) -> TailoredResumePolishResponse:
        return TailoredResumePolishResponse(
            text="# 郑文泽\n\n- 主导增长分析项目，推动关键指标提升。"
        )

    monkeypatch.setattr(
        "app.routers.tailored_resumes.polish_tailored_resume_markdown",
        fake_polish_tailored_resume_markdown,
    )

    app = create_app(
        Settings(
            resume_ai_provider="minimax",
            resume_ai_base_url="https://api.minimaxi.com/anthropic",
            resume_ai_api_key="test-key",
            resume_ai_model="MiniMax-M2.5",
        )
    )

    async def override_current_user() -> User:
        return User(
            id=uuid4(),
            email="polish@example.com",
            password_hash="hashed-password",
            nickname="Polish Tester",
        )

    app.dependency_overrides[get_current_user] = override_current_user

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/tailored-resumes/polish",
            json={"text": "# 郑文泽\n\n- 做增长分析"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["text"].startswith("# 郑文泽")
