from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=80)
    job_direction: str | None = Field(default=None, max_length=120)
    target_city: str | None = Field(default=None, max_length=80)
    target_role: str | None = Field(default=None, max_length=120)


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: EmailStr
    nickname: str | None
    job_direction: str | None
    target_city: str | None
    target_role: str | None
    created_at: datetime
    updated_at: datetime

