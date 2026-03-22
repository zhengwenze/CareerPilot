from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.core.responses import success_response
from app.db.session import get_db_session, get_session_factory
from app.models import User
from app.routers.deps import (
    get_current_user,
    get_settings_dependency,
)
from app.schemas.common import ApiSuccessResponse
from app.schemas.tailored_resume import (
    TailoredResumeGenerateFromSavedJobRequest,
    TailoredResumePdfToMarkdownResponse,
    TailoredResumeWorkflowResponse,
)
from app.services.resume import convert_pdf_bytes_to_markdown, validate_resume_upload
from app.services.resume_optimizer import get_resume_optimization_markdown_download
from app.services.tailored_resume import (
    generate_tailored_resume_for_saved_job,
    get_tailored_resume_workflow,
    list_tailored_resume_workflows,
)

router = APIRouter(prefix="/tailored-resumes", tags=["tailored-resumes"])


def resolve_session_factory(request: Request):
    return getattr(request.app.state, "session_factory", get_session_factory())


@router.get(
    "/workflows",
    response_model=ApiSuccessResponse[list[TailoredResumeWorkflowResponse]],
)
async def list_workflows(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[list[TailoredResumeWorkflowResponse]]:
    workflows = await list_tailored_resume_workflows(session, current_user=current_user)
    return success_response(request, workflows)


@router.get(
    "/workflows/{session_id}",
    response_model=ApiSuccessResponse[TailoredResumeWorkflowResponse],
)
async def get_workflow(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[TailoredResumeWorkflowResponse]:
    workflow = await get_tailored_resume_workflow(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, workflow)


@router.post(
    "/pdf-to-md",
    response_model=ApiSuccessResponse[TailoredResumePdfToMarkdownResponse],
)
async def convert_resume_pdf_to_markdown(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[TailoredResumePdfToMarkdownResponse]:
    del current_user
    file_name, _content_type, content = await validate_resume_upload(
        file,
        settings=settings,
    )
    markdown = await convert_pdf_bytes_to_markdown(content, file_name)
    if not markdown:
        raise ApiException(
            status_code=422,
            code=ErrorCode.BAD_REQUEST,
            message="PDF 转 Markdown 失败，未生成可用内容",
        )
    return success_response(
        request,
        TailoredResumePdfToMarkdownResponse(
            file_name=file_name,
            markdown=markdown,
        ),
    )


@router.post(
    "/optimize",
    response_model=ApiSuccessResponse[TailoredResumeWorkflowResponse],
)
async def optimize_tailored_resume_from_saved_records(
    request: Request,
    payload: TailoredResumeGenerateFromSavedJobRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[TailoredResumeWorkflowResponse]:
    workflow = await generate_tailored_resume_for_saved_job(
        session,
        current_user=current_user,
        payload=payload,
        session_factory=resolve_session_factory(request),
        settings=settings,
    )
    return success_response(request, workflow)


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
