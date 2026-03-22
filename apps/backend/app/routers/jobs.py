from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.db.session import get_db_session, get_session_factory
from app.models import User
from app.routers.deps import get_current_user
from app.schemas.common import ApiSuccessResponse
from app.schemas.job import JobCreateRequest, JobResponse, JobUpdateRequest
from app.services.job import (
    build_job_response,
    create_job,
    process_job_parse_job,
    serialize_job,
    update_job,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
        return


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
    job, parse_job = await create_job(
        session,
        current_user=current_user,
        payload=payload,
    )
    if parse_job is not None:
        schedule_job_parse_job(
            request.app,
            job_id=job.id,
            parse_job_id=parse_job.id,
        )
    return success_response(request, serialize_job(job, latest_parse_job=parse_job))


@router.put("/{job_id}", response_model=ApiSuccessResponse[JobResponse])
async def update_job_description(
    request: Request,
    job_id: UUID,
    payload: JobUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job, parse_job = await update_job(
        session,
        current_user=current_user,
        job_id=job_id,
        payload=payload,
    )
    if parse_job is not None:
        schedule_job_parse_job(
            request.app,
            job_id=job.id,
            parse_job_id=parse_job.id,
        )
    response = await build_job_response(
        session,
        job=job,
        latest_parse_job=parse_job,
    )
    return success_response(request, response)
