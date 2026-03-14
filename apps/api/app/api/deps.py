from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models import User
from app.services.auth import get_user_by_id
from app.services.token_blocklist import InMemoryTokenBlocklist, TokenBlocklist

bearer_scheme = HTTPBearer(auto_error=False)
fallback_blocklist = InMemoryTokenBlocklist()


async def get_token_blocklist(request: Request) -> TokenBlocklist:
    return getattr(request.app.state, "token_blocklist", fallback_blocklist)


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return credentials.credentials


async def get_current_token_payload(
    token: Annotated[str, Depends(get_bearer_token)],
    blocklist: Annotated[TokenBlocklist, Depends(get_token_blocklist)],
) -> dict[str, Any]:
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    jti = payload.get("jti")
    if not jti or await blocklist.contains(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is no longer valid",
        )

    return payload


async def get_current_user(
    payload: Annotated[dict[str, Any], Depends(get_current_token_payload)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing subject",
        )

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is malformed",
        ) from exc

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user
