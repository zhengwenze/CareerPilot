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
    status: str
    overall_score: Decimal
    rule_score: Decimal
    model_score: Decimal
    dimension_scores_json: dict[str, Any] = Field(default_factory=dict)
    gap_json: dict[str, Any] = Field(default_factory=dict)
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MatchReportDeleteResponse(BaseModel):
    message: str
