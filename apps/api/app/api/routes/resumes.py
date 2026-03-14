from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_object_storage, get_settings_dependency
from app.core.config import Settings
from app.core.responses import success_response
from app.db.session import get_db_session, get_session_factory
from app.models import User
from app.schemas.common import ApiSuccessResponse
from app.schemas.resume import (
    ResumeDownloadUrlResponse,
    ResumeParseJobResponse,
    ResumeResponse,
    ResumeStructuredUpdateRequest,
)
from app.services.resume import (
    create_resume_parse_job,
    generate_resume_download_url,
    get_resume_detail,
    list_resume_parse_jobs,
    list_resumes,
    process_resume_parse_job,
    serialize_resume,
    update_resume_structured_data,
    upload_resume,
)
from app.services.storage import ObjectStorage

router = APIRouter(prefix="/resumes", tags=["resumes"])


def resolve_session_factory(request: Request):
    return getattr(request.app.state, "session_factory", get_session_factory())


@router.post(
    "/upload",
    response_model=ApiSuccessResponse[ResumeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume_file(
    request: Request,
    background_tasks: BackgroundTasks,
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
        background_tasks.add_task(
            process_resume_parse_job,
            resume_id=resume.id,
            parse_job_id=resume.latest_parse_job.id,
            storage=storage,
            session_factory=resolve_session_factory(request),
        )
    return success_response(request, resume)


@router.get("", response_model=ApiSuccessResponse[list[ResumeResponse]])
async def get_resume_list(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[list[ResumeResponse]]:
    items = await list_resumes(session, current_user=current_user)
    return success_response(request, items)


@router.get("/{resume_id}", response_model=ApiSuccessResponse[ResumeResponse])
async def get_resume(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeResponse]:
    resume = await get_resume_detail(
        session,
        current_user=current_user,
        resume_id=resume_id,
    )
    return success_response(request, resume)


@router.get(
    "/{resume_id}/download-url",
    response_model=ApiSuccessResponse[ResumeDownloadUrlResponse],
)
async def get_resume_download_url(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[ResumeDownloadUrlResponse]:
    payload = await generate_resume_download_url(
        session,
        current_user=current_user,
        resume_id=resume_id,
        storage=storage,
        settings=settings,
    )
    return success_response(request, payload)


@router.get(
    "/{resume_id}/parse-jobs",
    response_model=ApiSuccessResponse[list[ResumeParseJobResponse]],
)
async def get_resume_parse_job_list(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[list[ResumeParseJobResponse]]:
    items = await list_resume_parse_jobs(
        session,
        current_user=current_user,
        resume_id=resume_id,
    )
    return success_response(request, items)


@router.post("/{resume_id}/parse", response_model=ApiSuccessResponse[ResumeResponse])
async def retry_resume_parse(
    request: Request,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(
        process_resume_parse_job,
        resume_id=resume.id,
        parse_job_id=parse_job.id,
        storage=storage,
        session_factory=resolve_session_factory(request),
    )
    return success_response(
        request,
        serialize_resume(resume, parse_job=parse_job),
    )


@router.put("/{resume_id}/structured", response_model=ApiSuccessResponse[ResumeResponse])
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
    return success_response(request, resume)
