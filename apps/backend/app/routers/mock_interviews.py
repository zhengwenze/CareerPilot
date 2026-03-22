from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.routers.deps import get_current_user, get_settings_dependency
from app.schemas.common import ApiSuccessResponse
from app.schemas.mock_interview import (
    MockInterviewAnswerSubmitRequest,
    MockInterviewAnswerSubmitResponse,
    MockInterviewDeleteResponse,
    MockInterviewSessionCreateRequest,
    MockInterviewSessionRecord,
)
from app.services.mock_interview import (
    create_mock_interview_session,
    delete_mock_interview_session,
    finish_mock_interview_session,
    get_mock_interview_session_detail,
    list_mock_interview_sessions,
    submit_mock_interview_answer,
)

router = APIRouter(prefix="/mock-interviews", tags=["mock-interviews"])


@router.post(
    "",
    response_model=ApiSuccessResponse[MockInterviewSessionRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: Request,
    payload: MockInterviewSessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings=Depends(get_settings_dependency),
) -> ApiSuccessResponse[MockInterviewSessionRecord]:
    created = await create_mock_interview_session(
        session,
        current_user=current_user,
        payload=payload,
        settings=settings,
    )
    return success_response(request, created)


@router.get("", response_model=ApiSuccessResponse[list[MockInterviewSessionRecord]])
async def list_sessions(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_id: Annotated[UUID | None, Query(alias="job_id")] = None,
) -> ApiSuccessResponse[list[MockInterviewSessionRecord]]:
    items = await list_mock_interview_sessions(
        session,
        current_user=current_user,
        job_id=job_id,
    )
    return success_response(request, items)


@router.get("/{session_id}", response_model=ApiSuccessResponse[MockInterviewSessionRecord])
async def get_session(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[MockInterviewSessionRecord]:
    detail = await get_mock_interview_session_detail(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, detail)


@router.post(
    "/{session_id}/turns/{turn_id}/answer",
    response_model=ApiSuccessResponse[MockInterviewAnswerSubmitResponse],
)
async def submit_answer(
    request: Request,
    session_id: UUID,
    turn_id: UUID,
    payload: MockInterviewAnswerSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings=Depends(get_settings_dependency),
) -> ApiSuccessResponse[MockInterviewAnswerSubmitResponse]:
    result = await submit_mock_interview_answer(
        session,
        current_user=current_user,
        session_id=session_id,
        turn_id=turn_id,
        answer_text=payload.answer_text,
        settings=settings,
    )
    return success_response(request, result)


@router.post("/{session_id}/finish", response_model=ApiSuccessResponse[MockInterviewSessionRecord])
async def finish_session(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings=Depends(get_settings_dependency),
) -> ApiSuccessResponse[MockInterviewSessionRecord]:
    result = await finish_mock_interview_session(
        session,
        current_user=current_user,
        session_id=session_id,
        settings=settings,
    )
    return success_response(request, result)


@router.delete("/{session_id}", response_model=ApiSuccessResponse[MockInterviewDeleteResponse])
async def delete_session(
    request: Request,
    session_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[MockInterviewDeleteResponse]:
    await delete_mock_interview_session(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return success_response(request, MockInterviewDeleteResponse(message="Mock interview deleted"))
