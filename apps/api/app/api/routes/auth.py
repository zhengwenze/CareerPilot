from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_token_payload,
    get_current_user,
    get_token_blocklist,
)
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.models import User
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
)
from app.schemas.user import UserResponse
from app.services.auth import (
    AuthenticationError,
    UserAlreadyExistsError,
    authenticate_user,
    register_user,
)
from app.services.token_blocklist import TokenBlocklist

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthTokenResponse:
    try:
        user = await register_user(
            session, payload.email, payload.password, payload.nickname
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    access_token, expires_in = create_access_token(str(user.id))
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthTokenResponse:
    try:
        user = await authenticate_user(session, payload.email, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    access_token, expires_in = create_access_token(str(user.id))
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    token_payload: Annotated[dict[str, object], Depends(get_current_token_payload)],
    blocklist: Annotated[TokenBlocklist, Depends(get_token_blocklist)],
) -> LogoutResponse:
    expires_at = datetime.fromtimestamp(int(token_payload["exp"]), tz=UTC)
    await blocklist.add(str(token_payload["jti"]), expires_at)
    return LogoutResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(current_user)
