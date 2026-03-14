from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiMeta(BaseModel):
    request_id: str
    timestamp: datetime


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiSuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: ApiMeta


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ApiErrorBody
    meta: ApiMeta

