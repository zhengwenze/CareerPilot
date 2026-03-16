from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MatchReport


def derive_fit_band(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "strong"
    if score >= 50:
        return "partial"
    return "weak"


async def mark_reports_stale_for_resume(
    session: AsyncSession,
    *,
    resume_id,
    resume_version: int,
) -> None:
    await session.execute(
        update(MatchReport)
        .where(
            MatchReport.resume_id == resume_id,
            MatchReport.resume_version < resume_version,
            MatchReport.stale_status != "stale",
        )
        .values(stale_status="stale")
    )


async def mark_reports_stale_for_job(
    session: AsyncSession,
    *,
    job_id,
    job_version: int,
) -> None:
    await session.execute(
        update(MatchReport)
        .where(
            MatchReport.jd_id == job_id,
            MatchReport.job_version < job_version,
            MatchReport.stale_status != "stale",
        )
        .values(stale_status="stale")
    )
