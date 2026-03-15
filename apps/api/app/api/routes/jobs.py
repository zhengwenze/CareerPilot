from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiSuccessResponse
from app.schemas.job import JobCreateRequest, JobDeleteResponse, JobResponse, JobUpdateRequest
from app.services.job import (
    create_job,
    delete_job,
    get_job_or_404,
    list_jobs,
    parse_job,
    serialize_job,
    update_job,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
    job = await create_job(session, current_user=current_user, payload=payload)
    return success_response(request, serialize_job(job))


@router.get("", response_model=ApiSuccessResponse[list[JobResponse]])
async def get_job_list(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    parse_status: Annotated[str | None, Query(max_length=20)] = None,
) -> ApiSuccessResponse[list[JobResponse]]:
    jobs = await list_jobs(
        session,
        current_user=current_user,
        keyword=keyword,
        parse_status=parse_status,
    )
    return success_response(request, [serialize_job(job) for job in jobs])


@router.get("/{job_id}", response_model=ApiSuccessResponse[JobResponse])
async def get_job_detail(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    return success_response(request, serialize_job(job))


@router.put("/{job_id}", response_model=ApiSuccessResponse[JobResponse])
async def update_job_description(
    request: Request,
    job_id: UUID,
    payload: JobUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job = await update_job(session, current_user=current_user, job_id=job_id, payload=payload)
    return success_response(request, serialize_job(job))


@router.post("/{job_id}/parse", response_model=ApiSuccessResponse[JobResponse])
async def retry_job_parse(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobResponse]:
    job = await parse_job(session, current_user=current_user, job_id=job_id)
    return success_response(request, serialize_job(job))


@router.delete("/{job_id}", response_model=ApiSuccessResponse[JobDeleteResponse])
async def delete_job_description(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[JobDeleteResponse]:
    payload = await delete_job(session, current_user=current_user, job_id=job_id)
    return success_response(request, payload)
