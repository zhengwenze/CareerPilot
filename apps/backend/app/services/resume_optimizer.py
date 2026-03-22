from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException, ErrorCode
from app.models import JobDescription, MatchReport, Resume, ResumeOptimizationSession, User
from app.schemas.resume_optimization import ResumeOptimizationSessionCreateRequest


def build_resume_fact_check_report(*, original_resume, optimized_resume) -> dict:
    del original_resume, optimized_resume
    return {"findings": []}


async def create_resume_optimization_session(
    session: AsyncSession,
    *,
    current_user: User,
    payload: ResumeOptimizationSessionCreateRequest,
) -> tuple[ResumeOptimizationSession, Resume, JobDescription, MatchReport]:
    report = await session.get(MatchReport, payload.match_report_id)
    if report is None or report.user_id != current_user.id:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Match report not found",
        )

    result = await session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.user_id == current_user.id,
            ResumeOptimizationSession.match_report_id == report.id,
        )
    )
    existing = result.scalar_one_or_none()
    resume = await session.get(Resume, report.resume_id)
    job = await session.get(JobDescription, report.jd_id)
    if resume is None or job is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Resume or job not found",
        )
    if existing is not None:
        return existing, resume, job, report

    session_record = ResumeOptimizationSession(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        source_resume_version=report.resume_version,
        source_job_version=report.job_version,
        status="draft",
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return session_record, resume, job, report


async def get_resume_optimization_markdown_download(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> tuple[str, str]:
    result = await session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.id == session_id,
            ResumeOptimizationSession.user_id == current_user.id,
        )
    )
    session_record = result.scalar_one_or_none()
    if session_record is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Tailored resume not found",
        )
    markdown = (session_record.tailored_resume_md or session_record.optimized_resume_md or "").strip()
    if not markdown:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Tailored resume markdown is not ready",
        )
    safe_name = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", "tailored_resume").strip("_")
    return markdown, f"{safe_name}_{str(session_record.id)[:8]}.md"
