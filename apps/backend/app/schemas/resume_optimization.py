from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.resume import ResumeStructuredData

ALLOWED_REWRITE_MODES = ("replace", "append", "compress", "reorder")


class ResumeOptimizationTaskState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    title: str
    instruction: str = ""
    target_section: str
    target_requirement: str = ""
    issue: str = ""
    available_evidence: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""
    risk_note: str = ""
    priority: int
    selected: bool = True
    anchor_source_ids: list[str] = Field(default_factory=list)
    rewrite_mode: Literal["replace", "append", "compress", "reorder"] = "replace"
    must_preserve_terms: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_instruction_fields(self) -> "ResumeOptimizationTaskState":
        if not self.rewrite_instruction and self.instruction:
            self.rewrite_instruction = self.instruction
        if not self.instruction and self.rewrite_instruction:
            self.instruction = self.rewrite_instruction
        if self.rewrite_mode not in ALLOWED_REWRITE_MODES:
            self.rewrite_mode = "replace"
        return self


class ResumeOptimizationSectionDraft(BaseModel):
    key: str
    label: str
    selected: bool = True
    original_text: str = ""
    suggested_text: str = ""
    mode: str = "replace"
    diagnostics: list[str] = Field(default_factory=list)


class ResumeOptimizationDownstreamContract(BaseModel):
    markdown_is_fact_source: bool = False
    applied_fact_source: str = "resume.structured_json"
    draft_fact_source: str = "resume_optimization_session.optimized_resume_json"
    default_interview_fact_source: str = "resume.structured_json"
    allowed_unapplied_fact_source: str = "resume_optimization_session.optimized_resume_json"
    prohibited_source: str = "resume_optimization_session.optimized_resume_md"


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
    diagnosis_json: dict[str, Any] = Field(default_factory=dict)
    rewrite_tasks: list[ResumeOptimizationTaskState] = Field(default_factory=list)
    draft_sections: dict[str, ResumeOptimizationSectionDraft] = Field(default_factory=dict)
    selected_tasks: list[ResumeOptimizationTaskState] = Field(default_factory=list)
    optimized_resume_json: ResumeStructuredData | None = None
    fact_check_report_json: dict[str, Any] = Field(default_factory=dict)
    optimized_resume_md: str = ""
    has_downloadable_markdown: bool = False
    downloadable_file_name: str | None = None
    downstream_contract: ResumeOptimizationDownstreamContract = Field(
        default_factory=ResumeOptimizationDownstreamContract
    )
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
    downstream_fact_source: str = "resume.structured_json"
