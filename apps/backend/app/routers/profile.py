from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import get_current_user
from app.core.responses import success_response
from app.db.session import get_db_session
from app.models import User
from app.schemas.common import ApiSuccessResponse
from app.schemas.profile import UserProfileResponse, UserProfileUpdateRequest
from app.services.profile import get_or_create_user_profile, update_user_profile

router = APIRouter(prefix="/profile", tags=["profile"])


def _serialize_profile(current_user: User, profile) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
        job_direction=profile.job_direction,
        target_city=profile.target_city,
        target_role=profile.target_role,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/me", response_model=ApiSuccessResponse[UserProfileResponse])
async def get_my_profile(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[UserProfileResponse]:
    profile = await get_or_create_user_profile(session, current_user)
    return success_response(request, _serialize_profile(current_user, profile))


@router.put("/me", response_model=ApiSuccessResponse[UserProfileResponse])
async def update_my_profile(
    request: Request,
    payload: UserProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[UserProfileResponse]:
    profile = await update_user_profile(session, current_user, payload)
    return success_response(request, _serialize_profile(current_user, profile))
