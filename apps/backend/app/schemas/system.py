from __future__ import annotations

from pydantic import BaseModel


class HealthStatusResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    database: str
    redis: str


class VersionResponse(BaseModel):
    name: str
    version: str
    environment: str
