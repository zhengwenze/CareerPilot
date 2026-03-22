from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.routers.deps import get_current_user, get_object_storage
from app.schemas.common import ApiSuccessResponse
from app.schemas.resume import ResumeResponse
from app.services.resume import get_resume_detail, list_resumes
from app.services.resume_parse_runtime import ensure_resume_parse_job_scheduled
from app.services.storage import ObjectStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=ApiSuccessResponse[list[ResumeResponse]])
async def get_resume_list(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> ApiSuccessResponse[list[ResumeResponse]]:
    logger.info("Fetching resume list: user_id=%s", current_user.id)
    items = await list_resumes(session, current_user=current_user)
    for item in items:
        ensure_resume_parse_job_scheduled(request.app, resume=item, storage=storage)
    return success_response(request, items)


@router.get("/{resume_id}", response_model=ApiSuccessResponse[ResumeResponse])
async def get_resume(
    request: Request,
    resume_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> ApiSuccessResponse[ResumeResponse]:
    logger.info("Fetching resume detail: user_id=%s resume_id=%s", current_user.id, resume_id)
    resume = await get_resume_detail(
        session,
        current_user=current_user,
        resume_id=resume_id,
    )
    ensure_resume_parse_job_scheduled(request.app, resume=resume, storage=storage)
    return success_response(request, resume)
