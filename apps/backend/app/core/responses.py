from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.schemas.common import ApiErrorBody, ApiErrorResponse, ApiMeta, ApiSuccessResponse


def build_meta(request: Request) -> ApiMeta:
    return ApiMeta(
        request_id=getattr(request.state, "request_id", "unknown"),
        timestamp=datetime.now(UTC),
    )


def success_response(request: Request, data: Any) -> ApiSuccessResponse[Any]:
    return ApiSuccessResponse[Any](data=data, meta=build_meta(request))


def error_response(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any | None = None,
) -> ApiErrorResponse:
    return ApiErrorResponse(
        error=ApiErrorBody(code=code, message=message, details=details),
        meta=build_meta(request),
    )

