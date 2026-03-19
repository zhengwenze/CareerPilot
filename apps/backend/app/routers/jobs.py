from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import get_current_user
from app.core.responses import success_response
from app.db.session import get_db_session, get_session_factory
from app.models import User
from app.schemas.common import ApiSuccessResponse
from app.schemas.job import (
    JobCreateRequest,
    JobDeleteResponse,
    JobResponse,
    JobUpdateRequest,
)
from app.services.job import (
    build_job_response,
    create_job,
    create_job_parse_job,
    delete_job,
    get_job_or_404,
    get_job_response_or_404,
    list_jobs,
    process_job_parse_job,
    serialize_job,
    update_job,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def should_schedule_job_parse_job(job: JobResponse) -> bool:
    parse_job = job.latest_parse_job
    return (
        parse_job is not None
        and job.parse_status in {"pending", "processing"}
        and parse_job.status in {"pending", "processing"}
    )


def resolve_session_factory(app: FastAPI):
    return getattr(app.state, "session_factory", get_session_factory())


async def run_job_parse_job(
    app: FastAPI,
    *,
    job_id: UUID,
    parse_job_id: UUID,
) -> None:
    try:
        await process_job_parse_job(
            job_id=job_id,
            parse_job_id=parse_job_id,
            session_factory=resolve_session_factory(app),
        )
    except Exception:
        logger.exception(
            "Job parse background job crashed: job_id=%s parse_job_id=%s",
            job_id,
            parse_job_id,
        )


def schedule_job_parse_job(
    app: FastAPI,
    *,
    job_id: UUID,
    parse_job_id: UUID,
) -> None:
    tasks: set[asyncio.Task[None]] = getattr(app.state, "job_parse_tasks", set())
    active_task_ids: set[UUID] = getattr(app.state, "job_parse_task_ids", set())
    app.state.job_parse_tasks = tasks
    app.state.job_parse_task_ids = active_task_ids

    if parse_job_id in active_task_ids:
        return

    task = asyncio.create_task(
        run_job_parse_job(
            app,
            job_id=job_id,
            parse_job_id=parse_job_id,
        )
    )
    tasks.add(task)
    active_task_ids.add(parse_job_id)

    def _cleanup(finished_task: asyncio.Task[None]) -> None:
        tasks.discard(finished_task)
        active_task_ids.discard(parse_job_id)

    task.add_done_callback(_cleanup)


def ensure_job_parse_job_scheduled(
    app: FastAPI,
    *,
    job: JobResponse,
) -> None:
    if not should_schedule_job_parse_job(job):
        return
    assert job.latest_parse_job is not None
    schedule_job_parse_job(
        app,
        job_id=job.id,
        parse_job_id=job.latest_parse_job.id,
    )


@router.post(
    "",
    response_model=ApiSuccessResponse[JobResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_job_description(
    request: Request,
    payload: JobCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job, parse_job = await create_job(session, current_user=current_user, payload=payload)
    response = serialize_job(job, latest_parse_job=parse_job)
    ensure_job_parse_job_scheduled(request.app, job=response)
    return success_response(request, response)


@router.get("", response_model=ApiSuccessResponse[list[JobResponse]])
async def get_job_list(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    parse_status: Annotated[str | None, Query(max_length=20)] = None,
    status_stage: Annotated[str | None, Query(max_length=40)] = None,
    priority: Annotated[int | None, Query(ge=1, le=5)] = None,
    stale: bool | None = None,
) -> ApiSuccessResponse[list[JobResponse]]:
    jobs = await list_jobs(
        session,
        current_user=current_user,
        keyword=keyword,
        parse_status=parse_status,
        status_stage=status_stage,
        priority=priority,
        stale=stale,
    )
    for item in jobs:
        ensure_job_parse_job_scheduled(request.app, job=item)
    return success_response(request, jobs)


@router.get("/{job_id}", response_model=ApiSuccessResponse[JobResponse])
async def get_job_detail(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job = await get_job_response_or_404(session, current_user=current_user, job_id=job_id)
    ensure_job_parse_job_scheduled(request.app, job=job)
    return success_response(request, job)


@router.put("/{job_id}", response_model=ApiSuccessResponse[JobResponse])
async def update_job_description(
    request: Request,
    job_id: UUID,
    payload: JobUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job, parse_job = await update_job(session, current_user=current_user, job_id=job_id, payload=payload)
    response = await build_job_response(session, job=job, latest_parse_job=parse_job)
    ensure_job_parse_job_scheduled(request.app, job=response)
    return success_response(request, response)


@router.post("/{job_id}/parse", response_model=ApiSuccessResponse[JobResponse])
async def retry_job_parse(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job, parse_job = await create_job_parse_job(
        session,
        current_user=current_user,
        job_id=job_id,
    )
    response = serialize_job(job, latest_parse_job=parse_job)
    ensure_job_parse_job_scheduled(request.app, job=response)
    return success_response(request, response)


@router.delete("/{job_id}", response_model=ApiSuccessResponse[JobDeleteResponse])
async def delete_job_description(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobDeleteResponse]:
    await get_job_or_404(session, current_user=current_user, job_id=job_id)
    payload = await delete_job(session, current_user=current_user, job_id=job_id)
    return success_response(request, payload)
