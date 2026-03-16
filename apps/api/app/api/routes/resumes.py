from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_object_storage, get_settings_dependency
from app.core.config import Settings
from app.core.responses import success_response
from app.db.session import get_db_session, get_session_factory
from app.models import User
from app.schemas.common import ApiSuccessResponse

logger = logging.getLogger(__name__)
from app.schemas.resume import (
    ResumeDeleteResponse,
    ResumeDownloadUrlResponse,
    ResumeParseJobResponse,
    ResumeResponse,
    ResumeStructuredUpdateRequest,
)
from app.services.resume import (
    create_resume_parse_job,
    delete_resume,
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


def resolve_session_factory(app: FastAPI):
    logger.info(
        "Resolved resume session factory from app state: has_custom_factory=%s",
        hasattr(app.state, "session_factory"),
    )
    return getattr(app.state, "session_factory", get_session_factory())


async def run_resume_parse_job(
    app: FastAPI,
    *,
    resume_id: UUID,
    parse_job_id: UUID,
    storage: ObjectStorage,
) -> None:
    logger.info(
        "Running scheduled resume parse task: resume_id=%s parse_job_id=%s",
        resume_id,
        parse_job_id,
    )
    try:
        await process_resume_parse_job(
            resume_id=resume_id,
            parse_job_id=parse_job_id,
            storage=storage,
            session_factory=resolve_session_factory(app),
        )
    except Exception:
        logger.exception(
            "Resume parse background job crashed: resume_id=%s parse_job_id=%s",
            resume_id,
            parse_job_id,
        )


def schedule_resume_parse_job(
    app: FastAPI,
    *,
    resume_id: UUID,
    parse_job_id: UUID,
    storage: ObjectStorage,
) -> None:
    tasks: set[asyncio.Task[None]] = getattr(app.state, "resume_parse_tasks", set())
    app.state.resume_parse_tasks = tasks

    logger.info(
        "Scheduling resume parse task: resume_id=%s parse_job_id=%s active_tasks_before=%s",
        resume_id,
        parse_job_id,
        len(tasks),
    )
    task = asyncio.create_task(
        run_resume_parse_job(
            app,
            resume_id=resume_id,
            parse_job_id=parse_job_id,
            storage=storage,
        )
    )
    tasks.add(task)
    logger.info(
        "Scheduled resume parse task: resume_id=%s parse_job_id=%s active_tasks_after=%s",
        resume_id,
        parse_job_id,
        len(tasks),
    )

    def _cleanup(finished_task: asyncio.Task[None]) -> None:
        tasks.discard(finished_task)
        logger.info(
            "Cleaned up resume parse task: resume_id=%s parse_job_id=%s cancelled=%s active_tasks_after=%s",
            resume_id,
            parse_job_id,
            finished_task.cancelled(),
            len(tasks),
        )
        if finished_task.cancelled():
            logger.warning(
                "Resume parse task cancelled: resume_id=%s parse_job_id=%s",
                resume_id,
                parse_job_id,
            )

    task.add_done_callback(_cleanup)


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
    logger.info(
        "Received resume upload request: user_id=%s file_name=%s content_type=%s",
        current_user.id,
        file.filename,
        file.content_type,
    )
    resume = await upload_resume(
        session,
        current_user=current_user,
        file=file,
        storage=storage,
        settings=settings,
    )
    if resume.latest_parse_job is not None:
        logger.info(
            "Queueing resume parse background job: resume_id=%s parse_job_id=%s",
            resume.id,
            resume.latest_parse_job.id,
        )
        schedule_resume_parse_job(
            request.app,
            resume_id=resume.id,
            parse_job_id=resume.latest_parse_job.id,
            storage=storage,
        )
    return success_response(request, resume)


@router.get("", response_model=ApiSuccessResponse[list[ResumeResponse]])
async def get_resume_list(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[list[ResumeResponse]]:
    logger.info("Fetching resume list: user_id=%s", current_user.id)
    items = await list_resumes(session, current_user=current_user)
    return success_response(request, items)


@router.get("/{resume_id}", response_model=ApiSuccessResponse[ResumeResponse])
async def get_resume(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeResponse]:
    logger.info("Fetching resume detail: user_id=%s resume_id=%s", current_user.id, resume_id)
    resume = await get_resume_detail(
        session,
        current_user=current_user,
        resume_id=resume_id,
    )
    return success_response(request, resume)


@router.delete("/{resume_id}", response_model=ApiSuccessResponse[ResumeDeleteResponse])
async def delete_resume_file(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> ApiSuccessResponse[ResumeDeleteResponse]:
    logger.info("Deleting resume: user_id=%s resume_id=%s", current_user.id, resume_id)
    payload = await delete_resume(
        session,
        current_user=current_user,
        resume_id=resume_id,
        storage=storage,
    )
    return success_response(request, payload)


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
    logger.info("Generating resume download url: user_id=%s resume_id=%s", current_user.id, resume_id)
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
    logger.info("Fetching resume parse jobs: user_id=%s resume_id=%s", current_user.id, resume_id)
    items = await list_resume_parse_jobs(
        session,
        current_user=current_user,
        resume_id=resume_id,
    )
    return success_response(request, items)


@router.post("/{resume_id}/parse", response_model=ApiSuccessResponse[ResumeResponse])
async def retry_resume_parse(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> ApiSuccessResponse[ResumeResponse]:
    logger.info("Retrying resume parse: user_id=%s resume_id=%s", current_user.id, resume_id)
    resume, parse_job = await create_resume_parse_job(
        session,
        current_user=current_user,
        resume_id=resume_id,
    )
    logger.info(
        "Queueing resume parse retry background job: resume_id=%s parse_job_id=%s",
        resume.id,
        parse_job.id,
    )
    schedule_resume_parse_job(
        request.app,
        resume_id=resume.id,
        parse_job_id=parse_job.id,
        storage=storage,
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
    logger.info(
        "Saving structured resume data: user_id=%s resume_id=%s education_count=%s work_count=%s project_count=%s",
        current_user.id,
        resume_id,
        len(payload.structured_json.education),
        len(payload.structured_json.work_experience),
        len(payload.structured_json.projects),
    )
    resume = await update_resume_structured_data(
        session,
        current_user=current_user,
        resume_id=resume_id,
        payload=payload,
    )
    return success_response(request, resume)
