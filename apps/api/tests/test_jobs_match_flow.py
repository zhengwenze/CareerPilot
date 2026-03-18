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


@pytest.mark.asyncio
async def test_jobs_match_flow_reaches_success_and_persists_actionable_report(
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
        settings=Settings(match_ai_provider="disabled"),
    )

    async with session_factory() as session:
        persisted_report = await session.get(MatchReport, report_id)
        persisted_job = await session.get(JobDescription, job_id)
        assert persisted_report is not None
        assert persisted_job is not None
        assert persisted_report.status == "success"
        assert persisted_report.stale_status == "fresh"
        assert persisted_report.fit_band in {"excellent", "strong", "partial", "weak"}
        assert persisted_report.scorecard_json.get("overall_score") is not None
        assert persisted_report.gap_json.get("actions")
        assert persisted_report.tailoring_plan_json.get("rewrite_tasks")
        assert persisted_report.interview_blueprint_json.get("question_pack")
        assert persisted_job.latest_match_report_id == persisted_report.id
        assert persisted_job.recommended_resume_id == resume_id
        assert persisted_job.status_stage in {"tailoring_needed", "interview_ready", "matched"}
