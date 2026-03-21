from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.tailored_resume import TailoredResumeGenerateRequest
from app.services.tailored_resume_document_ai import (
    AITailoredResumeDocumentRequest,
    build_tailored_resume_document_ai_provider,
)


def _mock_document_payload() -> dict[str, object]:
    return {
        "matchSummary": {
            "targetRole": "增长数据分析师",
            "optimizationLevel": "conservative",
            "matchedKeywords": ["Python", "SQL"],
            "missingButImportantKeywords": ["Tableau"],
            "overallStrategy": "保守优化，只在有证据处强化岗位相关表达。",
        },
        "basic": {
            "name": "郑文泽",
            "title": "增长数据分析师",
            "email": "zheng@example.com",
            "phone": "13800138000",
            "location": "上海",
            "links": [],
        },
        "summary": "负责数据分析与实验复盘。",
        "education": [],
        "experience": [],
        "projects": [],
        "skills": ["Python", "SQL"],
        "certificates": [],
        "languages": [],
        "awards": [],
        "customSections": [],
        "markdown": "# 郑文泽",
        "audit": {
            "truthfulnessStatus": "passed",
            "warnings": [],
            "changedSections": ["summary"],
            "addedKeywordsOnlyFromEvidence": True,
        },
    }


@pytest.mark.asyncio
async def test_tailored_resume_document_ai_provider_parses_full_document_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return _mock_document_payload()

    monkeypatch.setattr(
        "app.services.tailored_resume_document_ai.request_json_completion",
        fake_request_json_completion,
    )

    provider = build_tailored_resume_document_ai_provider(
        Settings(
            resume_ai_provider="minimax",
            resume_ai_base_url="https://api.minimaxi.com/anthropic",
            resume_ai_api_key="test-key",
            resume_ai_model="MiniMax-M2.5",
        )
    )
    result = await provider.generate(
        AITailoredResumeDocumentRequest(
            output_language="zh-CN",
            job_description="负责增长分析与实验分析",
            job_keywords=["Python", "SQL", "Tableau"],
            original_resume_json={"basic_info": {"name": "郑文泽"}},
            original_resume_markdown="# 郑文泽",
            optimization_level="conservative",
        )
    )

    assert result.status == "applied"
    assert result.payload is not None
    assert result.payload.matchSummary.optimizationLevel == "conservative"
    assert result.payload.markdown.startswith("# 郑文泽")


def test_tailored_resume_generate_request_rejects_non_conservative_optimization_level() -> None:
    with pytest.raises(ValidationError):
        TailoredResumeGenerateRequest.model_validate(
            {
                "resume_id": "00000000-0000-0000-0000-000000000001",
                "title": "增长数据分析师",
                "priority": 3,
                "jd_text": "负责增长分析",
                "optimization_level": "balanced",
            }
        )
