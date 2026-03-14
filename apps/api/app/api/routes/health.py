from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.responses import success_response
from app.db.session import get_db_session
from app.schemas.common import ApiSuccessResponse
from app.schemas.system import HealthStatusResponse, ReadinessResponse, VersionResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiSuccessResponse[HealthStatusResponse])
async def health(request: Request) -> ApiSuccessResponse[HealthStatusResponse]:
    return success_response(request, HealthStatusResponse(status="ok"))


@router.get("/health/readiness", response_model=ApiSuccessResponse[ReadinessResponse])
async def readiness(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiSuccessResponse[ReadinessResponse]:
    await session.execute(text("SELECT 1"))

    redis_client = getattr(request.app.state, "redis", None)
    redis_status = "skipped"
    if redis_client is not None:
        await redis_client.ping()
        redis_status = "ok"

    return success_response(
        request,
        ReadinessResponse(
            status="ready",
            database="ok",
            redis=redis_status,
        ),
    )


@router.get("/health/version", response_model=ApiSuccessResponse[VersionResponse])
async def version(request: Request) -> ApiSuccessResponse[VersionResponse]:
    settings = get_settings()
    return success_response(
        request,
        VersionResponse(
            name=settings.app_name,
            version=settings.app_version,
            environment=settings.app_env,
        ),
    )
