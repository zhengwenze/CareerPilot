from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ai_runtime import ContentChangeItem, ContentSegment, TaskState
from app.schemas.job import JobResponse
from app.schemas.resume import ResumeAIAttempt, ResumeResponse

TailoredResumeDisplayStatus = Literal[
    "idle",
    "processing",
    "segment_progress",
    "success",
    "failed",
    "cancelled",
    "returned",
    "aborted",
    "empty_result",
]


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


class TailoredResumeGenerateFromSavedJobRequest(BaseModel):
    resume_id: UUID
    job_id: UUID
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
    display_status: TailoredResumeDisplayStatus = "idle"
    fit_band: str
    overall_score: Decimal
    task_state: TaskState = Field(default_factory=TaskState)
    segments: list[ContentSegment] = Field(default_factory=list)
    change_items: list[ContentChangeItem] = Field(default_factory=list)
    document: TailoredResumeDocument = Field(default_factory=TailoredResumeDocument)
    error_message: str | None = None
    retryable: bool = False
    downloadable: bool = False
    result_is_empty: bool = False
    has_downloadable_markdown: bool = False
    downloadable_file_name: str | None = None
    created_at: datetime
    updated_at: datetime


class TailoredResumeWorkflowResponse(BaseModel):
    resume: ResumeResponse
    target_job: JobResponse
    tailored_resume: TailoredResumeArtifactResponse


class TailoredResumePdfToMarkdownResponse(BaseModel):
    file_name: str
    raw_markdown: str = ""
    cleaned_markdown: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    ai_used: bool = False
    ai_provider: str = ""
    ai_model: str = ""
    ai_error: str | None = None
    fallback_used: bool = False
    prompt_version: str = ""
    ai_latency_ms: int | None = None
    ai_path: Literal["primary", "secondary", "rules"]
    ai_attempts: list[ResumeAIAttempt] = Field(default_factory=list)
    ai_chain_latency_ms: int | None = None
    degraded_used: bool = False


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
