from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobStructuredBasic(BaseModel):
    title: str = ""
    company: str | None = None
    job_city: str | None = None
    employment_type: str | None = None


class JobStructuredRequirements(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    education: str | None = None
    experience_min_years: int | None = None


class JobStructuredData(BaseModel):
    basic: JobStructuredBasic = Field(default_factory=JobStructuredBasic)
    requirements: JobStructuredRequirements = Field(default_factory=JobStructuredRequirements)
    responsibilities: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    raw_summary: str | None = None


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    job_city: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default=None, max_length=50)
    source_name: str | None = Field(default=None, max_length=80)
    source_url: str | None = Field(default=None, max_length=2000)
    jd_text: str = Field(min_length=1)


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    job_city: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default=None, max_length=50)
    source_name: str | None = Field(default=None, max_length=80)
    source_url: str | None = Field(default=None, max_length=2000)
    jd_text: str | None = Field(default=None, min_length=1)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    company: str | None
    job_city: str | None
    employment_type: str | None
    source_name: str | None
    source_url: str | None
    jd_text: str
    parse_status: str
    parse_error: str | None
    structured_json: JobStructuredData | None = None
    created_at: datetime
    updated_at: datetime


class JobDeleteResponse(BaseModel):
    message: str
