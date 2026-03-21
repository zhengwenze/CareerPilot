from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.models import User
from app.routers.deps import get_current_user
from app.schemas.tailored_resume import TailoredResumeGrammarResponse
from app.services.tailored_resume_grammar import check_tailored_resume_grammar


@pytest.mark.asyncio
async def test_check_tailored_resume_grammar_returns_strict_error_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return {
            "errors": [
                {
                    "context": "负责做为数据分析负责人，；推进指标体系建设。",
                    "text": "做为",
                    "suggestion": "作为",
                    "reason": "错别字",
                    "type": "spelling",
                },
                {
                    "context": "负责做为数据分析负责人，；推进指标体系建设。",
                    "text": "，；",
                    "suggestion": "；",
                    "reason": "标点错误",
                    "type": "punctuation",
                },
            ]
        }

    monkeypatch.setattr(
        "app.services.tailored_resume_grammar.request_json_completion",
        fake_request_json_completion,
    )

    response = await check_tailored_resume_grammar(
        text="负责做为数据分析负责人，；推进指标体系建设。",
        settings=Settings(
            resume_ai_provider="minimax",
            resume_ai_base_url="https://api.minimaxi.com/anthropic",
            resume_ai_api_key="test-key",
            resume_ai_model="MiniMax-M2.5",
        ),
    )

    assert isinstance(response, TailoredResumeGrammarResponse)
    assert len(response.errors) == 2
    assert response.errors[0].text == "做为"
    assert response.errors[0].type == "spelling"
    assert response.errors[1].text == "，；"
    assert response.errors[1].type == "punctuation"


@pytest.mark.asyncio
async def test_tailored_resume_grammar_api_returns_success_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_check_tailored_resume_grammar(**_: object) -> TailoredResumeGrammarResponse:
        return TailoredResumeGrammarResponse(
            errors=[
                {
                    "context": "负责做为数据分析负责人。",
                    "text": "做为",
                    "suggestion": "作为",
                    "reason": "错别字",
                    "type": "spelling",
                }
            ]
        )

    monkeypatch.setattr(
        "app.routers.tailored_resumes.check_tailored_resume_grammar",
        fake_check_tailored_resume_grammar,
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
            email="grammar@example.com",
            password_hash="hashed-password",
            nickname="Grammar Tester",
        )

    app.dependency_overrides[get_current_user] = override_current_user

    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/tailored-resumes/grammar",
            json={"text": "负责做为数据分析负责人。"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["errors"][0]["text"] == "做为"
