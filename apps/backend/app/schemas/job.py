from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobParseJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobReadinessEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID
    resume_id: UUID | None
    match_report_id: UUID | None
    status_from: str | None
    status_to: str
    reason: str | None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class JobLatestMatchReportSummary(BaseModel):
    id: UUID
    status: str
    overall_score: Decimal
    fit_band: str
    stale_status: str
    resume_id: UUID
    resume_version: int
    created_at: datetime


class JobStructuredBasic(BaseModel):
    title: str = ""
    company: str | None = None
    job_city: str | None = None
    employment_type: str | None = None


class JobResponsibilityCluster(BaseModel):
    name: str
    items: list[str] = Field(default_factory=list)


class JobExperienceConstraints(BaseModel):
    education: str | None = None
    experience_min_years: int | None = None
    location: str | None = None
    employment_type: str | None = None


class JobDomainContext(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    seniority_hint: str | None = None
    summary: str | None = None
    benefits: list[str] = Field(default_factory=list)


class JobStructuredRequirements(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    education: str | None = None
    experience_min_years: int | None = None


class JobStructuredData(BaseModel):
    basic: JobStructuredBasic = Field(default_factory=JobStructuredBasic)
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    responsibility_clusters: list[JobResponsibilityCluster] = Field(default_factory=list)
    experience_constraints: JobExperienceConstraints = Field(default_factory=JobExperienceConstraints)
    domain_context: JobDomainContext = Field(default_factory=JobDomainContext)
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
    priority: int = Field(default=3, ge=1, le=5)
    jd_text: str = Field(min_length=1)
    recommended_resume_id: UUID | None = None


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    job_city: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default=None, max_length=50)
    source_name: str | None = Field(default=None, max_length=80)
    source_url: str | None = Field(default=None, max_length=2000)
    priority: int | None = Field(default=None, ge=1, le=5)
    jd_text: str | None = Field(default=None, min_length=1)
    recommended_resume_id: UUID | None = None


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
    latest_version: int
    priority: int
    status_stage: str
    recommended_resume_id: UUID | None
    latest_match_report_id: UUID | None
    parse_confidence: Decimal | None
    competency_graph_json: dict[str, Any] = Field(default_factory=dict)
    parse_status: str
    parse_error: str | None
    structured_json: JobStructuredData | None = None
    latest_parse_job: JobParseJobResponse | None = None
    latest_match_report: JobLatestMatchReportSummary | None = None
    recent_readiness_events: list[JobReadinessEventResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class JobDeleteResponse(BaseModel):
    message: str
