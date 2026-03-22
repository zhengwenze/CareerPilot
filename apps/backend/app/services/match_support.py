from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MatchReport, ResumeOptimizationSession


async def mark_reports_stale_for_resume(
    session: AsyncSession,
    *,
    resume_id,
    resume_version: int,
) -> None:
    result = await session.execute(
        select(MatchReport).where(MatchReport.resume_id == resume_id)
    )
    for report in result.scalars().all():
        report.stale_status = "stale"
        report.resume_version = resume_version
        session.add(report)


async def mark_reports_stale_for_job(
    session: AsyncSession,
    *,
    job_id,
    job_version: int,
) -> None:
    result = await session.execute(
        select(MatchReport).where(MatchReport.jd_id == job_id)
    )
    for report in result.scalars().all():
        report.stale_status = "stale"
        report.job_version = job_version
        session.add(report)

    session_result = await session.execute(
        select(ResumeOptimizationSession).where(ResumeOptimizationSession.jd_id == job_id)
    )
    for optimization_session in session_result.scalars().all():
        optimization_session.status = "stale"
        session.add(optimization_session)
