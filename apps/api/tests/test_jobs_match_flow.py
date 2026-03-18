from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import JobDescription, JobParseJob, MatchReport, Resume, User
from app.schemas.job import JobCreateRequest
from app.schemas.match_report import MatchReportCreateRequest
from app.schemas.resume import ResumeStructuredData
from app.services.job import create_job, process_job_parse_job
from app.services.match_report import create_match_report, process_match_report


def _resume_structured_data() -> ResumeStructuredData:
    return ResumeStructuredData(
        basic_info={
            "name": "郑文泽",
            "email": "zheng@example.com",
            "phone": "13800138000",
            "location": "上海",
            "summary": "负责数据分析与业务增长。",
        },
        education=["新疆大学 软件工程 本科 2023.09-2027.06"],
        work_experience=[
            "CareerPilot 数据分析实习生 负责指标体系搭建与实验复盘",
        ],
        projects=[
            "增长分析平台 搭建核心看板并推动实验分析闭环",
        ],
        skills={
            "technical": ["Python", "SQL"],
            "tools": ["Tableau"],
            "languages": ["English"],
        },
        certifications=["百度之星金奖"],
    )


async def _create_parsed_resume(session: AsyncSession, *, user: User) -> Resume:
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
        structured_json=_resume_structured_data().model_dump(),
        latest_version=1,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


def _mock_match_ai_payload() -> dict[str, object]:
    return {
        "overall_score": 82,
        "fit_band": "strong",
        "summary": "这份简历对目标岗位具备较强适配度，但还需要补强少量关键证据。",
        "reasoning": "核心技能与职责方向匹配较好，但部分高优先级要求的证据仍不够充分。",
        "confidence": 0.86,
        "strengths": [
            {
                "label": "Python 与 SQL",
                "reason": "简历中存在直接技能和项目证据。",
                "severity": "high",
            }
        ],
        "must_fix": [
            {
                "label": "实验分析结果量化",
                "reason": "当前描述缺少指标结果，难以支撑岗位要求。",
                "severity": "high",
            }
        ],
        "should_fix": [
            {
                "label": "跨团队协作场景",
                "reason": "可以增加业务协作细节来提升说服力。",
                "severity": "medium",
            }
        ],
        "evidence_map_json": {
            "matched_resume_fields": {
                "skills": ["Python", "SQL"],
                "projects": ["增长分析平台 搭建核心看板并推动实验分析闭环"],
            },
            "matched_jd_fields": {
                "required_skills": ["Python", "SQL", "Tableau"],
                "required_keywords": ["增长分析", "实验分析"],
            },
            "missing_items": ["实验分析结果量化"],
            "notes": ["AI 已根据岗位目标组织最终证据。"],
            "candidate_profile": {
                "skills": ["Python", "SQL", "Tableau"],
                "estimated_years": 1.5,
            },
        },
        "action_pack_json": {
            "resume_tailoring_tasks": [
                {
                    "priority": 1,
                    "title": "补强实验分析量化结果",
                    "instruction": "在项目经历中补充实验目标、指标提升和业务影响。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "interview_focus_areas": [
                {
                    "topic": "实验分析",
                    "reason": "需要用真实案例说明分析框架与结果。",
                    "priority": "high",
                }
            ],
            "missing_user_inputs": [
                {
                    "field": "metrics",
                    "question": "你是否有实验分析相关的指标提升数据可补充？",
                }
            ],
        },
        "tailoring_plan_json": {
            "target_summary": "增长数据分析师",
            "rewrite_tasks": [
                {
                    "priority": 1,
                    "title": "补强实验分析量化结果",
                    "instruction": "在项目经历中补充实验目标、指标提升和业务影响。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "must_add_evidence": ["实验分析结果量化"],
            "missing_info_questions": [
                {
                    "field": "metrics",
                    "question": "你是否有实验分析相关的指标提升数据可补充？",
                }
            ],
        },
        "interview_blueprint_json": {
            "target_role": "增长数据分析师",
            "focus_areas": [
                {
                    "topic": "实验分析",
                    "reason": "这是岗位的核心能力要求。",
                    "priority": "high",
                }
            ],
            "question_pack": [
                {
                    "topic": "实验分析",
                    "question": "请说明一次你主导实验分析并推动结果落地的经历。",
                    "intent": "验证真实项目证据与结果表达能力。",
                }
            ],
            "follow_up_rules": ["若只讲过程不讲结果，则追问量化指标。"],
            "rubric": [
                {
                    "dimension": "实验分析",
                    "weight": 30,
                    "criteria": "是否说清背景、方法、结果和业务影响。",
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_jobs_match_flow_reaches_success_and_persists_actionable_report(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return _mock_match_ai_payload()

    monkeypatch.setattr(
        "app.services.match_ai.request_json_completion",
        fake_request_json_completion,
    )

    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=test_user)
        job, parse_job = await create_job(
            session,
            current_user=test_user,
            payload=JobCreateRequest(
                title="数据分析师",
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
            ),
        )
        job_id = job.id
        parse_job_id = parse_job.id
        resume_id = resume.id

    assert parse_job.status == "pending"
    assert job.parse_status == "pending"

    await process_job_parse_job(
        job_id=job_id,
        parse_job_id=parse_job_id,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        parsed_job = await session.get(JobDescription, job_id)
        parsed_job_task = await session.get(JobParseJob, parse_job_id)
        assert parsed_job is not None
        assert parsed_job_task is not None
        assert parsed_job.parse_status == "success"
        assert parsed_job.status_stage == "analyzed"
        assert parsed_job.structured_json is not None
        assert parsed_job_task.status == "success"
        assert parsed_job_task.error_message is None

        report = await create_match_report(
            session,
            current_user=test_user,
            job_id=job_id,
            payload=MatchReportCreateRequest(
                resume_id=resume_id,
                force_refresh=True,
            ),
        )
        report_id = report.id
        assert report.status == "pending"

    await process_match_report(
        report_id=report_id,
        session_factory=session_factory,
        settings=Settings(
            match_ai_provider="minimax",
            match_ai_base_url="https://api.minimaxi.com/anthropic",
            match_ai_api_key="test-key",
            match_ai_model="MiniMax-M2.5",
        ),
    )

    async with session_factory() as session:
        persisted_report = await session.get(MatchReport, report_id)
        persisted_job = await session.get(JobDescription, job_id)
        assert persisted_report is not None
        assert persisted_job is not None
        assert persisted_report.status == "success"
        assert persisted_report.stale_status == "fresh"
        assert persisted_report.fit_band == "strong"
        assert persisted_report.scorecard_json.get("overall_score") is not None
        assert persisted_report.scorecard_json.get("generation_mode") == "ai_mandatory"
        assert persisted_report.gap_json.get("actions")
        assert persisted_report.tailoring_plan_json.get("rewrite_tasks")
        assert persisted_report.interview_blueprint_json.get("question_pack")
        assert persisted_job.latest_match_report_id == persisted_report.id
        assert persisted_job.recommended_resume_id == resume_id
        assert persisted_job.status_stage in {"tailoring_needed", "interview_ready", "matched"}


@pytest.mark.asyncio
async def test_jobs_match_flow_fails_when_match_ai_key_is_missing(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=test_user)
        job, parse_job = await create_job(
            session,
            current_user=test_user,
            payload=JobCreateRequest(
                title="数据分析师",
                company="CareerPilot",
                job_city="上海",
                employment_type="全职",
                source_name="Boss直聘",
                source_url="https://example.com/jobs/2",
                priority=3,
                jd_text="需要熟悉 Python、SQL、Tableau，并能负责增长分析与实验分析。",
            ),
        )
        job_id = job.id
        parse_job_id = parse_job.id
        resume_id = resume.id

    await process_job_parse_job(
        job_id=job_id,
        parse_job_id=parse_job_id,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        report = await create_match_report(
            session,
            current_user=test_user,
            job_id=job_id,
            payload=MatchReportCreateRequest(
                resume_id=resume_id,
                force_refresh=True,
            ),
        )
        report_id = report.id

    await process_match_report(
        report_id=report_id,
        session_factory=session_factory,
        settings=Settings(
            match_ai_provider="minimax",
            match_ai_base_url="https://api.minimaxi.com/anthropic",
            match_ai_api_key=None,
            match_ai_model="MiniMax-M2.5",
        ),
    )

    async with session_factory() as session:
        persisted_report = await session.get(MatchReport, report_id)
        assert persisted_report is not None
        assert persisted_report.status == "failed"
        assert "MATCH_AI_API_KEY" in (persisted_report.error_message or "")


@pytest.mark.asyncio
async def test_jobs_match_flow_fails_when_match_ai_payload_is_invalid(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return {
            "overall_score": 88,
            "fit_band": "excellent",
        }

    monkeypatch.setattr(
        "app.services.match_ai.request_json_completion",
        fake_request_json_completion,
    )

    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=test_user)
        job, parse_job = await create_job(
            session,
            current_user=test_user,
            payload=JobCreateRequest(
                title="数据分析师",
                company="CareerPilot",
                job_city="上海",
                employment_type="全职",
                source_name="Boss直聘",
                source_url="https://example.com/jobs/3",
                priority=3,
                jd_text="需要熟悉 Python、SQL、Tableau，并能负责增长分析与实验分析。",
            ),
        )
        job_id = job.id
        parse_job_id = parse_job.id
        resume_id = resume.id

    await process_job_parse_job(
        job_id=job_id,
        parse_job_id=parse_job_id,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        report = await create_match_report(
            session,
            current_user=test_user,
            job_id=job_id,
            payload=MatchReportCreateRequest(
                resume_id=resume_id,
                force_refresh=True,
            ),
        )
        report_id = report.id

    await process_match_report(
        report_id=report_id,
        session_factory=session_factory,
        settings=Settings(
            match_ai_provider="minimax",
            match_ai_base_url="https://api.minimaxi.com/anthropic",
            match_ai_api_key="test-key",
            match_ai_model="MiniMax-M2.5",
        ),
    )

    async with session_factory() as session:
        persisted_report = await session.get(MatchReport, report_id)
        assert persisted_report is not None
        assert persisted_report.status == "failed"
        assert "structured payload validation failed" in (
            persisted_report.error_message or ""
        )
