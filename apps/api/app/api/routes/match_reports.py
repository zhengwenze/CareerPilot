from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_settings_dependency
from app.core.config import Settings
from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiSuccessResponse
from app.schemas.match_report import (
    MatchReportCreateRequest,
    MatchReportDeleteResponse,
    MatchReportResponse,
)
from app.services.match_report import (
    create_match_report,
    delete_match_report,
    get_match_report_or_404,
    list_match_reports_by_job,
    serialize_match_report,
)
from app.services.match_ai import build_ai_match_correction_provider

router = APIRouter(tags=["match-reports"])


@router.post(
    "/jobs/{job_id}/match-reports",
    response_model=ApiSuccessResponse[MatchReportResponse],
)
async def create_match_report_for_job(
    request: Request,
    job_id: UUID,
    payload: MatchReportCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[MatchReportResponse]:
    report = await create_match_report(
        session,
        current_user=current_user,
        job_id=job_id,
        payload=payload,
        ai_provider=build_ai_match_correction_provider(settings),
    )
    return success_response(request, serialize_match_report(report))


@router.get(
    "/jobs/{job_id}/match-reports",
    response_model=ApiSuccessResponse[list[MatchReportResponse]],
)
async def get_match_report_list_by_job(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[list[MatchReportResponse]]:
    reports = await list_match_reports_by_job(session, current_user=current_user, job_id=job_id)
    return success_response(request, [serialize_match_report(report) for report in reports])


@router.get(
    "/match-reports/{report_id}",
    response_model=ApiSuccessResponse[MatchReportResponse],
)
async def get_match_report_detail(
    request: Request,
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[MatchReportResponse]:
    report = await get_match_report_or_404(session, current_user=current_user, report_id=report_id)
    return success_response(request, serialize_match_report(report))


@router.delete(
    "/match-reports/{report_id}",
    response_model=ApiSuccessResponse[MatchReportDeleteResponse],
)
async def delete_match_report_detail(
    request: Request,
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[MatchReportDeleteResponse]:
    payload = await delete_match_report(session, current_user=current_user, report_id=report_id)
    return success_response(request, payload)
