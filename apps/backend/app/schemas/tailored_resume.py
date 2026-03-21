from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.job import JobResponse
from app.schemas.resume import ResumeResponse


class TailoredResumeGenerateRequest(BaseModel):
    resume_id: UUID
    job_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    job_city: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default=None, max_length=50)
    source_name: str | None = Field(default=None, max_length=80)
    source_url: str | None = Field(default=None, max_length=2000)
    priority: int = Field(default=3, ge=1, le=5)
    jd_text: str = Field(min_length=1)
    force_refresh: bool = False


class TailoredResumeArtifactResponse(BaseModel):
    session_id: UUID
    match_report_id: UUID
    status: str
    fit_band: str
    overall_score: Decimal
    optimized_resume_md: str = ""
    has_downloadable_markdown: bool = False
    downloadable_file_name: str | None = None
    created_at: datetime
    updated_at: datetime


class TailoredResumeWorkflowResponse(BaseModel):
    resume: ResumeResponse
    target_job: JobResponse
    tailored_resume: TailoredResumeArtifactResponse
