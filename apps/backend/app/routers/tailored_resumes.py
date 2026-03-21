from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.responses import success_response
from app.db.session import get_db_session, get_session_factory
from app.models import User
from app.routers.deps import (
    get_current_user,
    get_object_storage,
    get_settings_dependency,
)
from app.routers.resumes import schedule_resume_parse_job
from app.schemas.common import ApiSuccessResponse
from app.schemas.resume import ResumeResponse
from app.schemas.tailored_resume import (
    TailoredResumeGrammarRequest,
    TailoredResumeGrammarResponse,
    TailoredResumeGenerateRequest,
    TailoredResumePolishRequest,
    TailoredResumePolishResponse,
    TailoredResumeWorkflowResponse,
)
from app.services.resume import upload_resume
from app.services.resume_optimizer import get_resume_optimization_markdown_download
from app.services.storage import ObjectStorage
from app.services.tailored_resume import (
    generate_tailored_resume_workflow,
    get_tailored_resume_workflow,
    list_tailored_resume_workflows,
)
from app.services.tailored_resume_grammar import check_tailored_resume_grammar
from app.services.tailored_resume_polish import polish_tailored_resume_markdown

router = APIRouter(prefix="/tailored-resumes", tags=["tailored-resumes"])


def resolve_session_factory(request: Request):
    return getattr(request.app.state, "session_factory", get_session_factory())


@router.post(
    "/resumes/upload",
    response_model=ApiSuccessResponse[ResumeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_primary_resume(
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


@router.get(
    "/workflows",
    response_model=ApiSuccessResponse[list[TailoredResumeWorkflowResponse]],
)
async def get_tailored_resume_workflow_list(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[list[TailoredResumeWorkflowResponse]]:
    payload = await list_tailored_resume_workflows(session, current_user=current_user)
    return success_response(request, payload)


@router.post(
    "/grammar",
    response_model=ApiSuccessResponse[TailoredResumeGrammarResponse],
)
async def check_tailored_resume_text_grammar(
    request: Request,
    payload: TailoredResumeGrammarRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[TailoredResumeGrammarResponse]:
    del current_user
    result = await check_tailored_resume_grammar(
        text=payload.text,
        settings=settings,
    )
    return success_response(request, result)


@router.post(
    "/polish",
    response_model=ApiSuccessResponse[TailoredResumePolishResponse],
)
async def polish_tailored_resume_text(
    request: Request,
    payload: TailoredResumePolishRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[TailoredResumePolishResponse]:
    del current_user
    result = await polish_tailored_resume_markdown(
        text=payload.text,
        settings=settings,
    )
    return success_response(request, result)


@router.post(
    "/workflows",
    response_model=ApiSuccessResponse[TailoredResumeWorkflowResponse],
)
async def create_tailored_resume_workflow(
    request: Request,
    payload: TailoredResumeGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[TailoredResumeWorkflowResponse]:
    workflow = await generate_tailored_resume_workflow(
        session,
        current_user=current_user,
        payload=payload,
        session_factory=resolve_session_factory(request),
        settings=settings,
    )
    return success_response(request, workflow)


@router.get(
    "/workflows/{session_id}",
    response_model=ApiSuccessResponse[TailoredResumeWorkflowResponse],
)
async def get_tailored_resume_workflow_detail(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[TailoredResumeWorkflowResponse]:
    payload = await get_tailored_resume_workflow(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, payload)


@router.get(
    "/workflows/{session_id}/download-markdown",
    response_class=PlainTextResponse,
)
async def download_tailored_resume_markdown(
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlainTextResponse:
    markdown_content, file_name = await get_resume_optimization_markdown_download(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return PlainTextResponse(
        content=markdown_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
