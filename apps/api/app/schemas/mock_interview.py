from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MockInterviewSessionCreateRequest(BaseModel):
    match_report_id: UUID
    mode: str = Field(default="general", min_length=1, max_length=30)
    optimization_session_id: UUID | None = None


class MockInterviewAnswerSubmitRequest(BaseModel):
    answer_text: str = Field(min_length=1, max_length=8000)


class MockInterviewTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    turn_index: int
    question_group_index: int
    question_source: str
    question_topic: str
    question_text: str
    question_intent: str | None
    question_rubric_json: list[dict[str, Any]] = Field(default_factory=list)
    answer_text: str | None
    answer_latency_seconds: int | None
    status: str
    evaluation_json: dict[str, Any] = Field(default_factory=dict)
    decision_json: dict[str, Any] = Field(default_factory=dict)
    asked_at: datetime | None
    answered_at: datetime | None
    evaluated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MockInterviewSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    resume_id: UUID
    jd_id: UUID
    match_report_id: UUID
    optimization_session_id: UUID | None
    source_resume_version: int
    source_job_version: int
    mode: str
    status: str
    current_question_index: int
    current_follow_up_count: int
    max_questions: int
    max_follow_ups_per_question: int
    plan_json: dict[str, Any] = Field(default_factory=dict)
    review_json: dict[str, Any] = Field(default_factory=dict)
    follow_up_tasks_json: list[dict[str, Any]] = Field(default_factory=list)
    overall_score: Decimal | None = None
    error_message: str | None
    current_turn: MockInterviewTurnResponse | None = None
    turns: list[MockInterviewTurnResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MockInterviewAnswerSubmitResponse(BaseModel):
    session_id: UUID
    submitted_turn_id: UUID
    submitted_turn_evaluation: dict[str, Any] = Field(default_factory=dict)
    next_action: dict[str, Any] = Field(default_factory=dict)


class MockInterviewReviewResponse(BaseModel):
    session_id: UUID
    status: str
    overall_score: Decimal | None = None
    review_json: dict[str, Any] = Field(default_factory=dict)
    follow_up_tasks_json: list[dict[str, Any]] = Field(default_factory=list)


class MockInterviewDeleteResponse(BaseModel):
    message: str
