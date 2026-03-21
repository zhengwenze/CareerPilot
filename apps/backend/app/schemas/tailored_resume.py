from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
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
    optimization_level: Literal["conservative"] = "conservative"


class TailoredResumeMatchSummary(BaseModel):
    targetRole: str = ""
    optimizationLevel: Literal["conservative"] = "conservative"
    matchedKeywords: list[str] = Field(default_factory=list)
    missingButImportantKeywords: list[str] = Field(default_factory=list)
    overallStrategy: str = ""


class TailoredResumeBasic(BaseModel):
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[str] = Field(default_factory=list)


class TailoredResumeEducationItem(BaseModel):
    school: str = ""
    major: str = ""
    degree: str = ""
    startDate: str = ""
    endDate: str = ""
    description: list[str] = Field(default_factory=list)


class TailoredResumeExperienceItem(BaseModel):
    company: str = ""
    position: str = ""
    startDate: str = ""
    endDate: str = ""
    bullets: list[str] = Field(default_factory=list)


class TailoredResumeProjectItem(BaseModel):
    name: str = ""
    role: str = ""
    startDate: str = ""
    endDate: str = ""
    bullets: list[str] = Field(default_factory=list)
    link: str = ""


class TailoredResumeCustomSectionItem(BaseModel):
    title: str = ""
    subtitle: str = ""
    years: str = ""
    description: list[str] = Field(default_factory=list)


class TailoredResumeCustomSection(BaseModel):
    title: str = ""
    items: list[TailoredResumeCustomSectionItem] = Field(default_factory=list)


class TailoredResumeAudit(BaseModel):
    truthfulnessStatus: Literal["passed", "warning"] = "passed"
    warnings: list[str] = Field(default_factory=list)
    changedSections: list[str] = Field(default_factory=list)
    addedKeywordsOnlyFromEvidence: bool = True


class TailoredResumeDocument(BaseModel):
    matchSummary: TailoredResumeMatchSummary = Field(default_factory=TailoredResumeMatchSummary)
    basic: TailoredResumeBasic = Field(default_factory=TailoredResumeBasic)
    summary: str = ""
    education: list[TailoredResumeEducationItem] = Field(default_factory=list)
    experience: list[TailoredResumeExperienceItem] = Field(default_factory=list)
    projects: list[TailoredResumeProjectItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    customSections: list[TailoredResumeCustomSection] = Field(default_factory=list)
    markdown: str = ""
    audit: TailoredResumeAudit = Field(default_factory=TailoredResumeAudit)


class TailoredResumeArtifactResponse(BaseModel):
    session_id: UUID
    match_report_id: UUID
    status: str
    fit_band: str
    overall_score: Decimal
    document: TailoredResumeDocument = Field(default_factory=TailoredResumeDocument)
    has_downloadable_markdown: bool = False
    downloadable_file_name: str | None = None
    created_at: datetime
    updated_at: datetime


class TailoredResumeWorkflowResponse(BaseModel):
    resume: ResumeResponse
    target_job: JobResponse
    tailored_resume: TailoredResumeArtifactResponse


class TailoredResumeGrammarRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class TailoredResumeGrammarErrorItem(BaseModel):
    context: str = Field(min_length=1)
    text: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    type: Literal["spelling", "punctuation"]


class TailoredResumeGrammarResponse(BaseModel):
    errors: list[TailoredResumeGrammarErrorItem] = Field(default_factory=list)


class TailoredResumePolishRequest(BaseModel):
    text: str = Field(min_length=1, max_length=30000)


class TailoredResumePolishResponse(BaseModel):
    text: str = Field(min_length=1)
