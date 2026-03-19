from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResumeOptimizationTaskState(BaseModel):
    key: str
    title: str
    instruction: str
    target_section: str
    priority: int
    selected: bool = True


class ResumeOptimizationSectionDraft(BaseModel):
    key: str
    label: str
    selected: bool = True
    original_text: str = ""
    suggested_text: str = ""
    mode: str = "replace"


class ResumeOptimizationContext(BaseModel):
    job_id: UUID
    match_report_id: UUID
    job_title: str
    company: str | None = None
    fit_band: str
    stale_status: str
    target_summary: str | None = None
    must_add_evidence: list[str] = Field(default_factory=list)
    gap_summary: list[str] = Field(default_factory=list)


class ResumeOptimizationSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    resume_id: UUID
    jd_id: UUID
    match_report_id: UUID
    source_resume_version: int
    source_job_version: int
    applied_resume_version: int | None
    status: str
    optimizer_context: ResumeOptimizationContext
    tailoring_plan_snapshot: dict[str, Any] = Field(default_factory=dict)
    draft_sections: dict[str, ResumeOptimizationSectionDraft] = Field(default_factory=dict)
    selected_tasks: list[ResumeOptimizationTaskState] = Field(default_factory=list)
    is_stale: bool
    created_at: datetime
    updated_at: datetime


class ResumeOptimizationSessionCreateRequest(BaseModel):
    match_report_id: UUID


class ResumeOptimizationSessionUpdateRequest(BaseModel):
    draft_sections: dict[str, ResumeOptimizationSectionDraft]
    selected_tasks: list[ResumeOptimizationTaskState]


class ResumeOptimizationApplyResponse(BaseModel):
    session_id: UUID
    resume_id: UUID
    applied_resume_version: int
