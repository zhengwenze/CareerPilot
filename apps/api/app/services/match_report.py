from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException, ErrorCode
from app.models import MatchReport, User
from app.schemas.match_report import MatchReportDeleteResponse, MatchReportResponse
from app.services.job import get_job_or_404


def serialize_match_report(report: MatchReport) -> MatchReportResponse:
    return MatchReportResponse(
        id=report.id,
        user_id=report.user_id,
        resume_id=report.resume_id,
        jd_id=report.jd_id,
        status=report.status,
        overall_score=report.overall_score,
        rule_score=report.rule_score,
        model_score=report.model_score,
        dimension_scores_json=report.dimension_scores_json or {},
        gap_json=report.gap_json or {},
        evidence_json=report.evidence_json or {},
        error_message=report.error_message,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


async def get_match_report_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    report_id: UUID,
) -> MatchReport:
    result = await session.execute(
        select(MatchReport).where(
            MatchReport.id == report_id,
            MatchReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Match report not found",
        )
    return report


async def list_match_reports_by_job(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
) -> list[MatchReport]:
    await get_job_or_404(session, current_user=current_user, job_id=job_id)
    result = await session.execute(
        select(MatchReport)
        .where(
            MatchReport.user_id == current_user.id,
            MatchReport.jd_id == job_id,
        )
        .order_by(desc(MatchReport.created_at))
    )
    return list(result.scalars().all())


async def delete_match_report(
    session: AsyncSession,
    *,
    current_user: User,
    report_id: UUID,
) -> MatchReportDeleteResponse:
    report = await get_match_report_or_404(session, current_user=current_user, report_id=report_id)
    await session.delete(report)
    await session.commit()
    return MatchReportDeleteResponse(message="Match report deleted successfully")
