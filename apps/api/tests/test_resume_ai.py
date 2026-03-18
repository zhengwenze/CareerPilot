from __future__ import annotations

import pytest

from app.services.ai_client import AIClientError
from app.services.resume_ai import (
    ConfiguredResumeAICorrectionProvider,
    ResumeAICorrectionRequest,
)


@pytest.mark.asyncio
async def test_resume_ai_accepts_valid_string_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return {
            "structured_json": {
                "basic_info": {
                    "name": "郑文泽",
                    "email": "zheng@example.com",
                    "phone": "13800138000",
                    "location": "北京",
                    "summary": "负责 AI 应用开发。",
                },
                "education": ["新疆大学 软件工程 本科 2023.09-2027.06"],
                "work_experience": ["CareerPilot AI 开发实习生 负责 Agent 工作流开发"],
                "projects": ["黑马点评 高可用秒杀系统 架构设计与实现"],
                "skills": {
                    "technical": ["Python", "FastAPI"],
                    "tools": ["Docker"],
                    "languages": ["English"],
                },
                "certifications": ["百度之星金奖"],
            },
            "corrections": [{"field": "education", "reason": "normalized"}],
            "confidence": 0.9,
            "reasoning": "ok",
        }

    monkeypatch.setattr(
        "app.services.resume_ai.request_json_completion",
        fake_request_json_completion,
    )

    provider = ConfiguredResumeAICorrectionProvider(
        provider="minimax",
        base_url="https://api.minimaxi.com/anthropic",
        api_key="test-key",
        model="MiniMax-M2.5",
        timeout_seconds=30,
    )

    result = await provider.correct(
        ResumeAICorrectionRequest(
            raw_text="郑文泽 新疆大学 软件工程 本科 黑马点评 百度之星金奖",
            rule_structured_json={},
        )
    )

    assert result.status == "applied"
    assert result.structured_data is not None
    assert result.structured_data.education == ["新疆大学 软件工程 本科 2023.09-2027.06"]
    assert result.structured_data.projects == ["黑马点评 高可用秒杀系统 架构设计与实现。"]


@pytest.mark.asyncio
async def test_resume_ai_normalizes_object_lists_to_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return {
            "structured_json": {
                "basic_info": {"name": "郑文泽", "email": "zheng@example.com"},
                "education": [
                    {
                        "school": "新疆大学",
                        "major": "软件工程",
                        "degree": "本科",
                        "start_date": "2023.09",
                        "end_date": "2027.06",
                        "notes": "211 双一流",
                    }
                ],
                "work_experience": [
                    {
                        "company": "CareerPilot",
                        "role": "AI 开发实习生",
                        "highlights": ["负责 Agent 工作流开发", "搭建简历解析模块"],
                    }
                ],
                "projects": [
                    {
                        "name": "黑马点评",
                        "summary": "高可用秒杀系统",
                        "outcome": "完成架构设计与实现",
                    }
                ],
                "skills": {
                    "technical": [{"name": "Python"}, "FastAPI"],
                    "tools": [["Docker", "Git"]],
                    "languages": ["English"],
                },
                "certifications": [
                    {"name": "百度之星金奖", "type": "竞赛"},
                    {"name": "精灵e站软件", "type": "软著"},
                ],
            },
            "confidence": 0.82,
            "corrections": [],
            "reasoning": "normalized",
        }

    monkeypatch.setattr(
        "app.services.resume_ai.request_json_completion",
        fake_request_json_completion,
    )

    provider = ConfiguredResumeAICorrectionProvider(
        provider="minimax",
        base_url="https://api.minimaxi.com/anthropic",
        api_key="test-key",
        model="MiniMax-M2.5",
        timeout_seconds=30,
    )

    result = await provider.correct(
        ResumeAICorrectionRequest(
            raw_text="郑文泽 新疆大学 软件工程 CareerPilot 黑马点评 百度之星金奖",
            rule_structured_json={},
        )
    )

    assert result.structured_data is not None
    assert result.structured_data.education == [
        "新疆大学 本科 软件工程 2023.09 2027.06 211 双一流"
    ]
    assert result.structured_data.projects == ["黑马点评 高可用秒杀系统 完成架构设计与实现。"]
    assert "CareerPilot AI 开发实习生 负责 Agent 工作流开发 搭建简历解析模块。" in (
        result.structured_data.work_experience
    )
    assert "Python" in result.structured_data.skills.technical
    assert "Docker Git" in result.structured_data.skills.tools
    assert result.structured_data.certifications == [
        "百度之星金奖 竞赛。",
        "精灵e站软件 软著。",
    ]


@pytest.mark.asyncio
async def test_resume_ai_raises_invalid_format_when_payload_cannot_be_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return {
            "structured_json": "not-an-object",
            "confidence": 0.1,
            "corrections": [],
            "reasoning": "bad",
        }

    monkeypatch.setattr(
        "app.services.resume_ai.request_json_completion",
        fake_request_json_completion,
    )

    provider = ConfiguredResumeAICorrectionProvider(
        provider="minimax",
        base_url="https://api.minimaxi.com/anthropic",
        api_key="test-key",
        model="MiniMax-M2.5",
        timeout_seconds=30,
    )

    with pytest.raises(AIClientError) as exc_info:
        await provider.correct(
            ResumeAICorrectionRequest(
                raw_text="郑文泽",
                rule_structured_json={},
            )
        )

    assert exc_info.value.category == "invalid_response_format"


@pytest.mark.asyncio
async def test_resume_ai_normalizes_cn_punctuation_to_professional_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return {
            "structured_json": {
                "basic_info": {
                    "name": "郑文泽",
                    "email": "zheng@example.com",
                    "phone": "13800138000",
                    "location": "北京",
                    "summary": "负责增长分析,实验分析;搭建指标体系",
                },
                "education": ["新疆大学 软件工程 本科 2023.09-2027.06"],
                "work_experience": ["CareerPilot 负责数据分析,推动实验体系"],
                "projects": ["增长平台:搭建看板,沉淀指标"],
                "skills": {
                    "technical": ["Python"],
                    "tools": ["Tableau"],
                    "languages": [],
                },
                "certifications": ["百度之星金奖,竞赛"],
            },
            "confidence": 0.83,
            "corrections": [],
            "reasoning": "normalized punctuation",
        }

    monkeypatch.setattr(
        "app.services.resume_ai.request_json_completion",
        fake_request_json_completion,
    )

    provider = ConfiguredResumeAICorrectionProvider(
        provider="minimax",
        base_url="https://api.minimaxi.com/anthropic",
        api_key="test-key",
        model="MiniMax-M2.5",
        timeout_seconds=30,
    )

    result = await provider.correct(
        ResumeAICorrectionRequest(
            raw_text="郑文泽 负责增长分析实验分析 搭建指标体系",
            rule_structured_json={},
        )
    )

    assert result.structured_data is not None
    assert result.structured_data.basic_info.summary == "负责增长分析，实验分析；搭建指标体系。"
    assert result.structured_data.work_experience == [
        "CareerPilot 负责数据分析，推动实验体系。"
    ]
    assert result.structured_data.projects == ["增长平台：搭建看板，沉淀指标。"]
    assert result.structured_data.certifications == ["百度之星金奖，竞赛。"]
