from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import MatchReport, Resume, ResumeOptimizationSession, User
from app.schemas.resume import ResumeStructuredData
from app.schemas.tailored_resume import TailoredResumeGenerateRequest
from app.services.resume_optimizer import get_resume_optimization_markdown_download
from app.services.tailored_resume import (
    generate_tailored_resume_workflow,
    get_tailored_resume_workflow,
    list_tailored_resume_workflows,
)


def _workflow_settings() -> Settings:
    return Settings(
        match_ai_provider="minimax",
        resume_ai_provider="minimax",
        resume_ai_api_key="test-key",
        resume_ai_model="MiniMax-M2.5",
        resume_ai_base_url="https://api.minimaxi.com/anthropic",
        match_ai_api_key="test-key",
        match_ai_model="MiniMax-M2.5",
        match_ai_base_url="https://api.minimaxi.com/anthropic",
    )


def _mock_match_ai_payload() -> dict[str, object]:
    return {
        "overall_score": 83,
        "fit_band": "strong",
        "summary": "主简历与目标岗位总体匹配，但需要用更贴近岗位语言的结果表达。",
        "reasoning": "技能和职责基础匹配，仍需补强量化结果和岗位关键词对齐。",
        "confidence": 0.88,
        "strengths": [
            {
                "label": "Python 与 SQL",
                "reason": "现有经历中已经有直接技能证据。",
                "severity": "high",
            }
        ],
        "must_fix": [
            {
                "label": "增长结果表述",
                "reason": "岗位强调业务结果，需要在经历中明确体现。",
                "severity": "high",
            }
        ],
        "should_fix": [
            {
                "label": "跨团队协作",
                "reason": "可以增加与业务团队协同推进的场景。",
                "severity": "medium",
            }
        ],
        "evidence_map_json": {
            "matched_resume_fields": {
                "skills": ["Python", "SQL", "Tableau"],
                "projects": ["增长分析平台 负责实验看板与指标复盘"],
            },
            "matched_jd_fields": {
                "required_skills": ["Python", "SQL", "Tableau"],
                "required_keywords": ["增长分析", "实验分析"],
            },
            "missing_items": ["增长结果表述"],
            "notes": ["AI 已根据岗位目标重组最终证据。"],
            "candidate_profile": {
                "skills": ["Python", "SQL", "Tableau"],
                "estimated_years": 1.5,
            },
        },
        "action_pack_json": {
            "resume_tailoring_tasks": [
                {
                    "priority": 1,
                    "title": "补强增长结果表述",
                    "instruction": "在工作经历与项目经历中补充业务结果和实验结论。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "interview_focus_areas": [
                {
                    "topic": "增长分析结果表达",
                    "reason": "岗位要求候选人能讲清结果与影响。",
                    "priority": "high",
                }
            ],
            "missing_user_inputs": [
                {
                    "field": "growth_metrics",
                    "question": "是否有能补充的增长结果指标？",
                }
            ],
        },
        "tailoring_plan_json": {
            "target_summary": "增长数据分析师",
            "rewrite_tasks": [
                {
                    "priority": 1,
                    "title": "补强增长结果表述",
                    "instruction": "在工作经历与项目经历中补充业务结果和实验结论。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "must_add_evidence": ["增长结果表述"],
            "missing_info_questions": [
                {
                    "field": "growth_metrics",
                    "question": "是否有能补充的增长结果指标？",
                }
            ],
        },
        "interview_blueprint_json": {
            "target_role": "增长数据分析师",
            "focus_areas": [
                {
                    "topic": "增长分析结果表达",
                    "reason": "这是岗位的核心考察点。",
                    "priority": "high",
                }
            ],
            "question_pack": [
                {
                    "topic": "增长分析结果表达",
                    "question": "请描述一次你推动增长分析结果落地的经历。",
                    "intent": "验证结果表达和真实项目证据。",
                }
            ],
            "follow_up_rules": ["若未提及指标，则追问业务结果。"],
            "rubric": [
                {
                    "dimension": "增长分析结果表达",
                    "weight": 30,
                    "criteria": "是否讲清背景、动作、结果和影响。",
                }
            ],
        },
    }


def _mock_tailored_resume_document_payload() -> dict[str, object]:
    return {
        "matchSummary": {
            "targetRole": "增长数据分析师",
            "optimizationLevel": "conservative",
            "matchedKeywords": ["Python", "SQL", "Tableau", "增长分析", "实验分析"],
            "missingButImportantKeywords": [],
            "overallStrategy": "保留原始事实与主要模块，并优先强化与目标岗位相关的表达。",
        },
        "basic": {
            "name": "郑文泽",
            "title": "增长数据分析师",
            "email": "zheng@example.com",
            "phone": "13800138000",
            "location": "上海",
            "links": [],
        },
        "summary": "负责数据分析、实验复盘与增长分析，保留原始经历事实并贴近目标岗位表达。",
        "education": [
            {
                "school": "新疆大学",
                "major": "软件工程",
                "degree": "本科",
                "startDate": "2023.09",
                "endDate": "2027.06",
                "description": [],
            }
        ],
        "experience": [
            {
                "company": "CareerPilot",
                "position": "数据分析实习生",
                "startDate": "",
                "endDate": "",
                "bullets": ["推进指标体系与增长分析，围绕实验复盘沉淀业务分析闭环。"],
            }
        ],
        "projects": [
            {
                "name": "增长分析平台",
                "role": "",
                "startDate": "",
                "endDate": "",
                "bullets": ["负责实验看板与指标复盘，支持团队持续跟踪关键增长问题。"],
                "link": "",
            }
        ],
        "skills": ["Python", "SQL", "Tableau"],
        "certificates": ["百度之星金奖"],
        "languages": ["English"],
        "awards": [],
        "customSections": [],
        "markdown": (
            "# 郑文泽\n"
            "增长数据分析师\n"
            "zheng@example.com | 13800138000 | 上海\n\n"
            "## Summary\n"
            "负责数据分析、实验复盘与增长分析，保留原始经历事实并贴近目标岗位表达。\n\n"
            "## Education\n"
            "- 新疆大学 软件工程 本科 | 2023.09 - 2027.06\n\n"
            "## Work Experience\n"
            "- CareerPilot 数据分析实习生\n"
            "  - 推进指标体系与增长分析，围绕实验复盘沉淀业务分析闭环。\n\n"
            "## Projects\n"
            "- 增长分析平台\n"
            "  - 负责实验看板与指标复盘，支持团队持续跟踪关键增长问题。\n\n"
            "## Skills\n"
            "- Python, SQL, Tableau\n"
        ),
        "audit": {
            "truthfulnessStatus": "passed",
            "warnings": [],
            "changedSections": ["summary", "experience", "projects"],
            "addedKeywordsOnlyFromEvidence": True,
        },
    }


def _resume_structured_data() -> ResumeStructuredData:
    return ResumeStructuredData(
        basic_info={
            "name": "郑文泽",
            "email": "zheng@example.com",
            "phone": "13800138000",
            "location": "上海",
            "summary": "负责数据分析与实验复盘。",
        },
        education=["新疆大学 软件工程 本科 2023.09-2027.06"],
        education_items=[
            {
                "id": "edu_1",
                "school": "新疆大学",
                "major": "软件工程",
                "degree": "本科",
                "start_date": "2023.09",
                "end_date": "2027.06",
                "honors": [],
                "source_refs": ["edu_1"],
            }
        ],
        work_experience=["CareerPilot 数据分析实习生 推进指标体系与增长分析"],
        work_experience_items=[
            {
                "id": "work_1",
                "company": "CareerPilot",
                "title": "数据分析实习生",
                "start_date": "",
                "end_date": "",
                "bullets": [
                    {
                        "id": "work_1_b1",
                        "text": "推进指标体系与增长分析",
                        "source_refs": ["work_1"],
                    }
                ],
                "source_refs": ["work_1"],
            }
        ],
        projects=["增长分析平台 负责实验看板与指标复盘"],
        project_items=[
            {
                "id": "proj_1",
                "name": "增长分析平台",
                "role": "",
                "start_date": "",
                "end_date": "",
                "summary": "负责实验看板与指标复盘",
                "bullets": [
                    {
                        "id": "proj_1_b1",
                        "text": "负责实验看板与指标复盘",
                        "source_refs": ["proj_1"],
                    }
                ],
                "source_refs": ["proj_1"],
            }
        ],
        skills={
            "technical": ["Python", "SQL"],
            "tools": ["Tableau"],
            "languages": ["English"],
        },
        certifications=["百度之星金奖"],
        certification_items=[
            {
                "id": "cert_1",
                "name": "百度之星金奖",
                "source_refs": ["cert_1"],
            }
        ],
    )


async def _create_parsed_resume(session: AsyncSession, *, user: User) -> Resume:
    structured = _resume_structured_data()
    resume = Resume(
        id=uuid4(),
        user_id=user.id,
        file_name="resume.pdf",
        file_url="minio://career-pilot/resume.pdf",
        storage_bucket="career-pilot",
        storage_object_key=f"resumes/{user.id}/resume.pdf",
        content_type="application/pdf",
        file_size=1024,
        parse_status="success",
        parse_error=None,
        raw_text=(
            "郑文泽 上海 数据分析 SQL Python 指标体系 实验分析 "
            "增长分析 CareerPilot 数据分析实习生"
        ),
        structured_json=structured.model_dump(),
        parse_artifacts_json={
            "canonical_resume_md": (
                "# 郑文泽\n"
                "zheng@example.com | 13800138000 | 上海\n\n"
                "## Summary\n"
                "负责数据分析与实验复盘。\n\n"
                "## Education\n"
                "- 新疆大学 软件工程 本科 2023.09-2027.06\n\n"
                "## Work Experience\n"
                "- CareerPilot 数据分析实习生 推进指标体系与增长分析\n\n"
                "## Projects\n"
                "- 增长分析平台 负责实验看板与指标复盘\n"
            )
        },
        latest_version=1,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


@pytest.mark.asyncio
async def test_tailored_resume_workflow_runs_end_to_end_and_preserves_canonical_resume(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_match_completion(**_: object) -> dict[str, object]:
        return _mock_match_ai_payload()

    async def fake_document_completion(**_: object) -> dict[str, object]:
        return _mock_tailored_resume_document_payload()

    monkeypatch.setattr(
        "app.services.match_ai.request_json_completion",
        fake_match_completion,
    )
    monkeypatch.setattr(
        "app.services.tailored_resume_document_ai.request_json_completion",
        fake_document_completion,
    )

    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=test_user)
        original_structured_json = resume.structured_json
        workflow = await generate_tailored_resume_workflow(
            session,
            current_user=test_user,
            payload=TailoredResumeGenerateRequest(
                resume_id=resume.id,
                title="增长数据分析师",
                company="CareerPilot",
                job_city="上海",
                employment_type="全职",
                source_name="Boss直聘",
                source_url="https://example.com/jobs/1",
                priority=3,
                jd_text=(
                    "岗位职责\n"
                    "- 负责增长分析与实验分析，搭建指标体系\n"
                    "- 与业务团队协作推进数据项目\n"
                    "任职要求\n"
                    "- 本科及以上，2年以上经验\n"
                    "- 熟练使用 Python、SQL、Tableau"
                ),
                force_refresh=True,
                optimization_level="conservative",
            ),
            session_factory=session_factory,
            settings=_workflow_settings(),
        )

        assert workflow.resume.id == resume.id
        assert workflow.resume.parse_status == "success"
        assert workflow.target_job.parse_status == "success"
        assert workflow.target_job.title == "增长数据分析师"
        assert workflow.tailored_resume.status == "ready"
        assert workflow.tailored_resume.fit_band == "strong"
        assert workflow.tailored_resume.document.matchSummary.optimizationLevel == "conservative"
        assert workflow.tailored_resume.document.matchSummary.targetRole == "增长数据分析师"
        assert workflow.tailored_resume.document.markdown.startswith("# 郑文泽")
        assert "## Work Experience" in workflow.tailored_resume.document.markdown
        assert workflow.tailored_resume.document.audit.truthfulnessStatus == "passed"
        assert workflow.tailored_resume.has_downloadable_markdown is True
        assert workflow.tailored_resume.downloadable_file_name is not None

        detail = await get_tailored_resume_workflow(
            session,
            current_user=test_user,
            session_id=workflow.tailored_resume.session_id,
        )
        workflows = await list_tailored_resume_workflows(
            session,
            current_user=test_user,
        )
        downloaded_markdown, file_name = await get_resume_optimization_markdown_download(
            session,
            current_user=test_user,
            session_id=workflow.tailored_resume.session_id,
        )

        assert detail.tailored_resume.session_id == workflow.tailored_resume.session_id
        assert detail.tailored_resume.document.markdown == workflow.tailored_resume.document.markdown
        assert len(workflows) == 1
        assert workflows[0].tailored_resume.document.markdown == workflow.tailored_resume.document.markdown
        assert downloaded_markdown.strip() == workflow.tailored_resume.document.markdown.strip()
        assert file_name.endswith(".md")

        await session.refresh(resume)
        assert resume.structured_json == original_structured_json
        assert resume.latest_version == 1

    async with session_factory() as session:
        persisted_resume = await session.get(Resume, resume.id)
        persisted_report = await session.get(
            MatchReport,
            workflow.tailored_resume.match_report_id,
        )
        persisted_session = await session.get(
            ResumeOptimizationSession,
            workflow.tailored_resume.session_id,
        )

        assert persisted_resume is not None
        assert persisted_resume.structured_json == original_structured_json
        assert persisted_report is not None
        assert persisted_report.status == "success"
        assert persisted_session is not None
        assert persisted_session.status == "ready"
        assert persisted_session.tailored_resume_md.startswith("# 郑文泽")
        assert persisted_session.tailored_resume_json["matchSummary"]["optimizationLevel"] == "conservative"
        assert persisted_session.audit_report_json["document_audit"]["truthfulnessStatus"] == "passed"


@pytest.mark.asyncio
async def test_tailored_resume_workflow_uses_deterministic_fallback_when_resume_ai_is_unavailable(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=test_user)
        workflow = await generate_tailored_resume_workflow(
            session,
            current_user=test_user,
            payload=TailoredResumeGenerateRequest(
                resume_id=resume.id,
                title="增长数据分析师",
                company="CareerPilot",
                job_city="上海",
                employment_type="全职",
                source_name="Boss直聘",
                source_url="https://example.com/jobs/2",
                priority=3,
                jd_text=(
                    "岗位职责\n"
                    "- 负责增长分析与实验分析，搭建指标体系\n"
                    "- 与业务团队协作推进数据项目\n"
                    "任职要求\n"
                    "- 本科及以上，2年以上经验\n"
                    "- 熟练使用 Python、SQL、Tableau"
                ),
                force_refresh=True,
                optimization_level="conservative",
            ),
            session_factory=session_factory,
            settings=Settings(
                match_ai_provider="minimax",
                match_ai_base_url="https://api.minimaxi.com/anthropic",
                match_ai_api_key=None,
                match_ai_model="MiniMax-M2.5",
                resume_ai_provider="disabled",
                resume_ai_base_url="https://api.minimaxi.com/anthropic",
                resume_ai_api_key=None,
                resume_ai_model="MiniMax-M2.5",
            ),
        )

        assert workflow.resume.id == resume.id
        assert workflow.target_job.parse_status == "success"
        assert workflow.tailored_resume.status == "ready"
        assert workflow.tailored_resume.has_downloadable_markdown is True
        assert workflow.tailored_resume.document.audit.truthfulnessStatus == "warning"
        assert "AI 不可用" in workflow.tailored_resume.document.audit.warnings[0]
        assert workflow.tailored_resume.document.markdown.startswith("# 郑文泽")

    async with session_factory() as session:
        persisted_report = await session.get(
            MatchReport,
            workflow.tailored_resume.match_report_id,
        )
        persisted_session = await session.get(
            ResumeOptimizationSession,
            workflow.tailored_resume.session_id,
        )

        assert persisted_report is not None
        assert persisted_report.status == "success"
        assert (
            persisted_report.scorecard_json.get("generation_mode")
            == "rule_semantic_fallback"
        )
        assert persisted_session is not None
        assert persisted_session.status == "ready"
        assert persisted_session.audit_report_json["document_audit"]["truthfulnessStatus"] == "warning"
