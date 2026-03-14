from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import ApiException, ErrorCode
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models import User
from app.services.auth import get_user_by_id
from app.services.storage import ObjectStorage
from app.services.token_blocklist import InMemoryTokenBlocklist, TokenBlocklist

bearer_scheme = HTTPBearer(auto_error=False)
fallback_blocklist = InMemoryTokenBlocklist()


async def get_token_blocklist(request: Request) -> TokenBlocklist:
    return getattr(request.app.state, "token_blocklist", fallback_blocklist)


async def get_object_storage(request: Request) -> ObjectStorage:
    storage = getattr(request.app.state, "object_storage", None)
    if storage is None:
        raise ApiException(
            status_code=503,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Object storage is not configured",
        )
    return storage


def get_settings_dependency() -> Settings:
    return get_settings()


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None:
        raise ApiException(
            status_code=401,
            code=ErrorCode.AUTH_MISSING_TOKEN,
            message="Missing bearer token",
        )
    return credentials.credentials


async def get_current_token_payload(
    token: Annotated[str, Depends(get_bearer_token)],
    blocklist: Annotated[TokenBlocklist, Depends(get_token_blocklist)],
) -> dict[str, Any]:
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError as exc:
        raise ApiException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Token has expired",
        ) from exc
    except InvalidTokenError as exc:
        raise ApiException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Invalid token",
        ) from exc

    jti = payload.get("jti")
    if not jti or await blocklist.contains(jti):
        raise ApiException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_REVOKED,
            message="Token is no longer valid",
        )

    return payload


async def get_current_user(
    payload: Annotated[dict[str, Any], Depends(get_current_token_payload)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    subject = payload.get("sub")
    if not subject:
        raise ApiException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_SUBJECT_INVALID,
            message="Token is missing subject",
        )

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise ApiException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_SUBJECT_INVALID,
            message="Token subject is malformed",
        ) from exc

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise ApiException(
            status_code=401,
            code=ErrorCode.AUTH_USER_NOT_FOUND,
            message="User not found",
        )
    if user.status != "active":
        raise ApiException(
            status_code=403,
            code=ErrorCode.AUTH_USER_DISABLED,
            message="User account is disabled",
        )

    return user
