from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_settings_dependency
from app.core.config import Settings
from app.core.responses import success_response
from app.db.session import get_db_session, get_session_factory
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
    process_match_report,
    serialize_match_report,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["match-reports"])


def resolve_session_factory(app):
    return getattr(app.state, "session_factory", get_session_factory())


async def run_match_report_job(app, *, report_id: UUID, settings: Settings) -> None:
    try:
        await process_match_report(
            report_id=report_id,
            session_factory=resolve_session_factory(app),
            settings=settings,
        )
    except Exception:
        logger.exception("Match report background job crashed: report_id=%s", report_id)


def schedule_match_report_job(app, *, report_id: UUID, settings: Settings) -> None:
    tasks: set[asyncio.Task[None]] = getattr(app.state, "match_report_tasks", set())
    active_task_ids: set[UUID] = getattr(app.state, "match_report_task_ids", set())
    app.state.match_report_tasks = tasks
    app.state.match_report_task_ids = active_task_ids

    if report_id in active_task_ids:
        return

    task = asyncio.create_task(run_match_report_job(app, report_id=report_id, settings=settings))
    tasks.add(task)
    active_task_ids.add(report_id)

    def _cleanup(finished_task: asyncio.Task[None]) -> None:
        tasks.discard(finished_task)
        active_task_ids.discard(report_id)

    task.add_done_callback(_cleanup)


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
    )
    if report.status == "pending":
        schedule_match_report_job(request.app, report_id=report.id, settings=settings)
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
