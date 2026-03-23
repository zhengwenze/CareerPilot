from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai_runtime import TaskState


class MockInterviewSessionCreateRequest(BaseModel):
    job_id: UUID
    resume_optimization_session_id: UUID


class MockInterviewAnswerSubmitRequest(BaseModel):
    answer_text: str = Field(min_length=1)


class MockInterviewDeleteResponse(BaseModel):
    message: str


class MockInterviewRetryPrepResponse(BaseModel):
    recorded: bool = True


class MockInterviewTurnDecision(BaseModel):
    need_comment: bool = False
    comment_text: str = ""
    next_action: Literal["followup", "next_main", "end"] = "next_main"
    next_question: str = ""
    reason: str = ""


class MockInterviewReviewSummary(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class MockInterviewTurnRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    turn_index: int
    question_text: str
    question_type: Literal["main", "followup"]
    main_question_id: str
    answer_text: str | None = None
    comment_text: str | None = None
    decision_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MockInterviewSessionRecord(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    resume_optimization_session_id: UUID | None
    source_job_version: int
    source_resume_version: int
    status: str
    question_count: int
    main_question_index: int
    followup_count_for_current_main: int
    max_questions: int
    max_followups_per_main: int
    prep_state: TaskState = Field(default_factory=TaskState)
    current_turn: MockInterviewTurnRecord | None = None
    turns: list[MockInterviewTurnRecord] = Field(default_factory=list)
    review: MockInterviewReviewSummary = Field(default_factory=MockInterviewReviewSummary)
    ending_text: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class MockInterviewAnswerSubmitResponse(BaseModel):
    session_id: UUID
    submitted_turn_id: UUID
    next_action: dict[str, Any] = Field(default_factory=dict)
