from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import get_current_user, get_settings_dependency
from app.core.config import Settings
from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiSuccessResponse
from app.schemas.mock_interview import (
    MockInterviewAnswerSubmitRequest,
    MockInterviewAnswerSubmitResponse,
    MockInterviewDeleteResponse,
    MockInterviewReviewResponse,
    MockInterviewSessionCreateRequest,
    MockInterviewSessionResponse,
)
from app.services.mock_interview import (
    create_mock_interview_session,
    delete_mock_interview_session,
    finish_mock_interview_session,
    get_mock_interview_review,
    get_mock_interview_session,
    list_mock_interview_sessions,
    submit_mock_interview_answer,
)

router = APIRouter(prefix="/mock-interviews", tags=["mock-interviews"])


@router.post(
    "",
    response_model=ApiSuccessResponse[MockInterviewSessionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_mock_interview_session_entry(
    request: Request,
    payload: MockInterviewSessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[MockInterviewSessionResponse]:
    result = await create_mock_interview_session(
        session,
        current_user=current_user,
        payload=payload,
        settings=settings,
    )
    return success_response(request, result)


@router.get(
    "",
    response_model=ApiSuccessResponse[list[MockInterviewSessionResponse]],
)
async def list_mock_interview_sessions_entry(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_id: UUID | None = Query(default=None),
    resume_id: UUID | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    mode: str | None = Query(default=None),
) -> ApiSuccessResponse[list[MockInterviewSessionResponse]]:
    result = await list_mock_interview_sessions(
        session,
        current_user=current_user,
        job_id=job_id,
        resume_id=resume_id,
        status=status_value,
        mode=mode,
    )
    return success_response(request, result)


@router.get(
    "/{session_id}",
    response_model=ApiSuccessResponse[MockInterviewSessionResponse],
)
async def get_mock_interview_session_entry(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[MockInterviewSessionResponse]:
    result = await get_mock_interview_session(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, result)


@router.post(
    "/{session_id}/turns/{turn_id}/answer",
    response_model=ApiSuccessResponse[MockInterviewAnswerSubmitResponse],
)
async def submit_mock_interview_answer_entry(
    request: Request,
    session_id: UUID,
    turn_id: UUID,
    payload: MockInterviewAnswerSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[MockInterviewAnswerSubmitResponse]:
    result = await submit_mock_interview_answer(
        session,
        current_user=current_user,
        session_id=session_id,
        turn_id=turn_id,
        payload=payload,
        settings=settings,
    )
    return success_response(request, result)


@router.post(
    "/{session_id}/finish",
    response_model=ApiSuccessResponse[MockInterviewReviewResponse],
)
async def finish_mock_interview_session_entry(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> ApiSuccessResponse[MockInterviewReviewResponse]:
    result = await finish_mock_interview_session(
        session,
        current_user=current_user,
        session_id=session_id,
        settings=settings,
    )
    return success_response(request, result)


@router.get(
    "/{session_id}/review",
    response_model=ApiSuccessResponse[MockInterviewReviewResponse],
)
async def get_mock_interview_review_entry(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[MockInterviewReviewResponse]:
    result = await get_mock_interview_review(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, result)


@router.delete(
    "/{session_id}",
    response_model=ApiSuccessResponse[MockInterviewDeleteResponse],
)
async def delete_mock_interview_session_entry(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[MockInterviewDeleteResponse]:
    result = await delete_mock_interview_session(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, result)
