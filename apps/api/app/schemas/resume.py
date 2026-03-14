from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResumeBasicInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""


class ResumeSkills(BaseModel):
    technical: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class ResumeStructuredData(BaseModel):
    basic_info: ResumeBasicInfo = Field(default_factory=ResumeBasicInfo)
    education: list[str] = Field(default_factory=list)
    work_experience: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    skills: ResumeSkills = Field(default_factory=ResumeSkills)
    certifications: list[str] = Field(default_factory=list)


class ResumeParseJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResumeResponse(BaseModel):
    id: UUID
    user_id: UUID
    file_name: str
    file_url: str
    storage_bucket: str
    storage_object_key: str
    content_type: str
    file_size: int
    parse_status: str
    parse_error: str | None
    raw_text: str | None = None
    structured_json: ResumeStructuredData | None = None
    latest_version: int
    created_at: datetime
    updated_at: datetime
    latest_parse_job: ResumeParseJobResponse | None = None
    download_url: str | None = None


class ResumeDownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int


class ResumeStructuredUpdateRequest(BaseModel):
    structured_json: ResumeStructuredData
