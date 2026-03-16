from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MatchReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    resume_id: UUID
    jd_id: UUID
    resume_version: int
    job_version: int
    status: str
    fit_band: str
    stale_status: str
    overall_score: Decimal
    rule_score: Decimal
    model_score: Decimal
    dimension_scores_json: dict[str, Any] = Field(default_factory=dict)
    gap_json: dict[str, Any] = Field(default_factory=dict)
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    scorecard_json: dict[str, Any] = Field(default_factory=dict)
    evidence_map_json: dict[str, Any] = Field(default_factory=dict)
    gap_taxonomy_json: dict[str, Any] = Field(default_factory=dict)
    action_pack_json: dict[str, Any] = Field(default_factory=dict)
    tailoring_plan_json: dict[str, Any] = Field(default_factory=dict)
    interview_blueprint_json: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MatchReportCreateRequest(BaseModel):
    resume_id: UUID
    force_refresh: bool = False


class MatchReportDeleteResponse(BaseModel):
    message: str
