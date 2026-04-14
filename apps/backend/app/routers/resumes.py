from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.routers.deps import (
    get_current_user,
    get_object_storage,
    get_settings_dependency,
)
from app.schemas.common import ApiSuccessResponse
from app.schemas.resume import ResumeResponse, ResumeStructuredUpdateRequest
from app.services.resume import (
    create_resume_parse_job,
    get_resume_detail,
    list_resumes,
    serialize_resume,
    update_resume_structured_data,
    upload_resume,
)
from app.services.resume_parse_runtime import schedule_resume_parse_job
from app.services.storage import ObjectStorage
from app.services.tailored_resume_autostart import maybe_autostart_tailored_resume

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=ApiSuccessResponse[list[ResumeResponse]])
async def list_resume_records(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[list[ResumeResponse]]:
    items = await list_resumes(session, current_user=current_user)
    return success_response(request, items)


@router.get("/{resume_id}", response_model=ApiSuccessResponse[ResumeResponse])
async def get_resume_record(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeResponse]:
    item = await get_resume_detail(session, current_user=current_user, resume_id=resume_id)
    return success_response(request, item)


@router.post(
    "/upload",
    response_model=ApiSuccessResponse[ResumeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume_file(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[ResumeResponse]:
    resume = await upload_resume(
        session,
        current_user=current_user,
        file=file,
        storage=storage,
        settings=settings,
    )
    if resume.latest_parse_job is not None:
        schedule_resume_parse_job(
            request.app,
            resume_id=resume.id,
            parse_job_id=resume.latest_parse_job.id,
            storage=storage,
        )
    return success_response(request, resume)


@router.put(
    "/{resume_id}/structured", response_model=ApiSuccessResponse[ResumeResponse]
)
async def save_resume_structured_data(
    request: Request,
    resume_id: UUID,
    payload: ResumeStructuredUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeResponse]:
    resume = await update_resume_structured_data(
        session,
        current_user=current_user,
        resume_id=resume_id,
        payload=payload,
    )
    if payload.trigger_job_id is not None:
        await maybe_autostart_tailored_resume(
            request.app,
            user_id=current_user.id,
            resume_id=resume.id,
            job_id=payload.trigger_job_id,
        )
    return success_response(request, resume)


@router.post("/{resume_id}/parse", response_model=ApiSuccessResponse[ResumeResponse])
async def retry_resume_parse(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> ApiSuccessResponse[ResumeResponse]:
    resume, parse_job = await create_resume_parse_job(
        session,
        current_user=current_user,
        resume_id=resume_id,
    )
    schedule_resume_parse_job(
        request.app,
        resume_id=resume.id,
        parse_job_id=parse_job.id,
        storage=storage,
    )
    return success_response(request, serialize_resume(resume, parse_job=parse_job))
