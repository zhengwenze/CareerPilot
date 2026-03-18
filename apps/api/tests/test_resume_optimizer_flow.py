from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import (
    JobReadinessEvent,
    MatchReport,
    Resume,
    ResumeOptimizationSession,
    User,
)
from app.schemas.job import JobCreateRequest
from app.schemas.match_report import MatchReportCreateRequest
from app.schemas.resume import ResumeStructuredData
from app.schemas.resume_optimization import ResumeOptimizationSessionCreateRequest
from app.services.job import create_job, process_job_parse_job
from app.services.match_report import create_match_report, process_match_report
from app.services.resume_optimizer import (
    apply_resume_optimization_session,
    create_resume_optimization_session,
    generate_resume_optimization_suggestions,
    get_resume_optimization_session,
)


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
        work_experience=["CareerPilot 数据分析实习生 推进指标体系与增长分析"],
        projects=["业务增长分析平台 从0到1搭建实验看板"],
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


async def _create_ready_match_report(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    user: User,
) -> tuple[UUID, UUID, UUID]:
    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=user)
        job, parse_job = await create_job(
            session,
            current_user=user,
            payload=JobCreateRequest(
                title="增长数据分析师",
                company="CareerPilot",
                job_city="上海",
                employment_type="全职",
                source_name="Boss直聘",
                source_url="https://example.com/jobs/optimizer",
                priority=2,
                jd_text=(
                    "岗位职责\n"
                    "- 负责增长分析、实验分析与指标体系建设\n"
                    "- 联动业务团队推进优化策略落地\n"
                    "任职要求\n"
                    "- 本科及以上，2年以上经验\n"
                    "- 熟练使用 Python、SQL、Tableau"
                ),
            ),
        )
        resume_id = resume.id
        job_id = job.id
        parse_job_id = parse_job.id

    await process_job_parse_job(
        job_id=job_id,
        parse_job_id=parse_job_id,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        report = await create_match_report(
            session,
            current_user=user,
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
        settings=Settings(match_ai_provider="disabled"),
    )
    return resume_id, job_id, report_id


@pytest.mark.asyncio
async def test_resume_optimizer_flow_applies_changes_and_marks_report_stale(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
) -> None:
    resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
    )

    async with session_factory() as session:
        session_record, _resume, _job, _report = await create_resume_optimization_session(
            session,
            current_user=test_user,
            payload=ResumeOptimizationSessionCreateRequest(match_report_id=report_id),
        )
        session_id = session_record.id
        assert session_record.status == "draft"
        assert session_record.applied_resume_version is None

        generated = await generate_resume_optimization_suggestions(
            session,
            current_user=test_user,
            session_id=session_id,
        )
        assert generated.status == "ready"
        assert generated.draft_sections["summary"].suggested_text.strip() != ""

        apply_result = await apply_resume_optimization_session(
            session,
            current_user=test_user,
            session_id=session_id,
        )
        assert apply_result.resume_id == resume_id
        assert apply_result.applied_resume_version == 2

        refreshed = await get_resume_optimization_session(
            session,
            current_user=test_user,
            session_id=session_id,
        )
        assert refreshed.status == "applied"
        assert refreshed.applied_resume_version == 2
        assert refreshed.is_stale is True

    async with session_factory() as session:
        persisted_resume = await session.get(Resume, resume_id)
        persisted_report = await session.get(MatchReport, report_id)
        persisted_session = await session.get(ResumeOptimizationSession, session_id)
        readiness_events = await session.scalars(
            select(JobReadinessEvent).where(
                JobReadinessEvent.match_report_id == report_id,
                JobReadinessEvent.status_to == "tailoring_applied",
            )
        )

        assert persisted_resume is not None
        assert persisted_report is not None
        assert persisted_session is not None
        assert persisted_resume.latest_version == 2
        assert persisted_report.stale_status == "stale"
        assert persisted_session.status == "applied"
        assert persisted_session.applied_resume_version == 2
        assert len(list(readiness_events)) >= 1
