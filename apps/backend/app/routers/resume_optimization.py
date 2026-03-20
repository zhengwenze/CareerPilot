from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings as get_settings_dependency
from app.routers.deps import get_current_user
from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiSuccessResponse
from app.schemas.resume_optimization import (
    ResumeOptimizationApplyResponse,
    ResumeOptimizationSessionCreateRequest,
    ResumeOptimizationSessionResponse,
    ResumeOptimizationSessionUpdateRequest,
)
from app.services.resume_optimizer import (
    apply_resume_optimization_session,
    create_resume_optimization_session,
    generate_resume_optimization_suggestions,
    get_resume_optimization_session,
    get_resume_optimization_markdown_download,
    serialize_resume_optimization_session,
    update_resume_optimization_session,
)

router = APIRouter(prefix="/resume-optimization-sessions", tags=["resume-optimization"])


@router.post(
    "",
    response_model=ApiSuccessResponse[ResumeOptimizationSessionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_resume_optimization_session_entry(
    request: Request,
    payload: ResumeOptimizationSessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeOptimizationSessionResponse]:
    session_record, _resume, job, report = await create_resume_optimization_session(
        session,
        current_user=current_user,
        payload=payload,
    )
    return success_response(
        request,
        serialize_resume_optimization_session(session_record, job=job, report=report),
    )


@router.get(
    "/{session_id}",
    response_model=ApiSuccessResponse[ResumeOptimizationSessionResponse],
)
async def get_resume_optimization_session_entry(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeOptimizationSessionResponse]:
    payload = await get_resume_optimization_session(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, payload)


@router.post(
    "/{session_id}/suggestions",
    response_model=ApiSuccessResponse[ResumeOptimizationSessionResponse],
)
async def generate_resume_optimization_session_suggestions(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[ResumeOptimizationSessionResponse]:
    payload = await generate_resume_optimization_suggestions(
        session,
        current_user=current_user,
        session_id=session_id,
        settings=settings,
    )
    return success_response(request, payload)


@router.put(
    "/{session_id}",
    response_model=ApiSuccessResponse[ResumeOptimizationSessionResponse],
)
async def update_resume_optimization_session_entry(
    request: Request,
    session_id: UUID,
    payload: ResumeOptimizationSessionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeOptimizationSessionResponse]:
    next_payload = await update_resume_optimization_session(
        session,
        current_user=current_user,
        session_id=session_id,
        payload=payload,
    )
    return success_response(request, next_payload)


@router.post(
    "/{session_id}/apply",
    response_model=ApiSuccessResponse[ResumeOptimizationApplyResponse],
)
async def apply_resume_optimization_session_entry(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ResumeOptimizationApplyResponse]:
    payload = await apply_resume_optimization_session(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, payload)


@router.get(
    "/{session_id}/download-markdown",
    response_class=PlainTextResponse,
)
async def download_resume_optimization_markdown_entry(
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
