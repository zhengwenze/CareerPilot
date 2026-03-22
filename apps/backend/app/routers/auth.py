from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.models import User
from app.routers.deps import (
    get_current_token_payload,
    get_current_user,
    get_token_blocklist,
)
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
)
from app.schemas.common import ApiSuccessResponse
from app.schemas.user import UserResponse
from app.services.auth import (
    authenticate_user,
    register_user,
)
from app.services.token_blocklist import TokenBlocklist

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiSuccessResponse[AuthTokenResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[AuthTokenResponse]:
    user = await register_user(
        session, payload.email, payload.password, payload.nickname
    )

    access_token, expires_in = create_access_token(str(user.id))
    return success_response(
        request,
        AuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse.model_validate(user),
        ),
    )


@router.post("/login", response_model=ApiSuccessResponse[AuthTokenResponse])
async def login(
    request: Request,
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[AuthTokenResponse]:
    user = await authenticate_user(session, payload.email, payload.password)

    access_token, expires_in = create_access_token(str(user.id))
    return success_response(
        request,
        AuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse.model_validate(user),
        ),
    )


@router.post("/logout", response_model=ApiSuccessResponse[LogoutResponse])
async def logout(
    request: Request,
    token_payload: Annotated[dict[str, object], Depends(get_current_token_payload)],
    blocklist: Annotated[TokenBlocklist, Depends(get_token_blocklist)],
) -> ApiSuccessResponse[LogoutResponse]:
    expires_at = datetime.fromtimestamp(int(token_payload["exp"]), tz=UTC)
    await blocklist.add(str(token_payload["jti"]), expires_at)
    return success_response(request, LogoutResponse(message="Logged out successfully"))


@router.get("/me", response_model=ApiSuccessResponse[UserResponse])
async def me(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiSuccessResponse[UserResponse]:
    return success_response(request, UserResponse.model_validate(current_user))
