from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MOCK_INTERVIEW_MAIN_QUESTION_SOURCES = (
    "strength",
    "gap",
    "behavioral_general",
)
MOCK_INTERVIEW_SCORE_DIMENSIONS = (
    "relevance",
    "specificity",
    "evidence",
    "structure",
    "communication",
)


class MockInterviewSessionCreateRequest(BaseModel):
    match_report_id: UUID
    mode: str = Field(default="general", min_length=1, max_length=30)
    optimization_session_id: UUID | None = None


class MockInterviewAnswerSubmitRequest(BaseModel):
    answer_text: str = Field(min_length=1, max_length=8000)


class MockInterviewFocusArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    priority: Literal["high", "medium", "low"] = "medium"


class MockInterviewQuestionRubricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(min_length=1)
    weight: int = Field(ge=1, le=100)
    criteria: str = Field(min_length=1)


class MockInterviewQuestionPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_index: int = Field(ge=1)
    source: Literal["strength", "gap", "behavioral_general"]
    topic: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    follow_up_rule: str | None = None
    rubric: list[MockInterviewQuestionRubricItem] = Field(default_factory=list)


class MockInterviewEndingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_questions: int = Field(ge=1, le=6)
    max_follow_ups_per_question: int = Field(ge=1, le=1)


class MockInterviewPlanJson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_summary: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    target_role: str | None = None
    focus_areas: list[MockInterviewFocusArea] = Field(default_factory=list)
    question_plan: list[MockInterviewQuestionPlanItem] = Field(
        default_factory=list,
        min_length=1,
        max_length=6,
    )
    ending_rule: MockInterviewEndingRule

    @model_validator(mode="after")
    def validate_question_categories(self) -> "MockInterviewPlanJson":
        categories = {item.source for item in self.question_plan}
        missing = [
            source
            for source in MOCK_INTERVIEW_MAIN_QUESTION_SOURCES
            if source not in categories
        ]
        if missing:
            raise ValueError(
                "question_plan must cover strength, gap, and behavioral_general questions"
            )
        if len(self.question_plan) > self.ending_rule.max_questions:
            raise ValueError("question_plan cannot exceed ending_rule.max_questions")
        return self


class MockInterviewDimensionScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relevance: int = Field(ge=0, le=5)
    specificity: int = Field(ge=0, le=5)
    evidence: int = Field(ge=0, le=5)
    structure: int = Field(ge=0, le=5)
    communication: int = Field(ge=0, le=5)


class MockInterviewEvaluationJson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension_scores: MockInterviewDimensionScores
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)


class MockInterviewDecisionQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    intent: str = Field(min_length=1)


class MockInterviewDecisionJson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["follow_up", "next_question", "finish_and_review"]
    reason: str = Field(min_length=1)
    next_question: MockInterviewDecisionQuestion | None = None

    @model_validator(mode="after")
    def validate_next_question(self) -> "MockInterviewDecisionJson":
        if self.type == "follow_up" and self.next_question is None:
            raise ValueError("next_question is required when decision type is follow_up")
        if self.type != "follow_up" and self.next_question is not None:
            raise ValueError("next_question is only allowed for follow_up decisions")
        return self


class MockInterviewInsightItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    severity: Literal["high", "medium", "low"] = "medium"


class MockInterviewQuestionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_group_index: int = Field(ge=1)
    source: Literal["strength", "gap", "behavioral_general", "follow_up"]
    question_text: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    suggested_better_answer: str = Field(min_length=1)


class MockInterviewFollowUpTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    task_type: Literal["resume", "interview"]
    instruction: str = Field(min_length=1)
    target_section: str | None = None
    reason: str = Field(min_length=1)
    source: str = Field(default="mock_interview_review", min_length=1)


class MockInterviewJobReadinessSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class MockInterviewReviewJson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: float = Field(ge=0.0, le=100.0)
    overall_summary: str = Field(min_length=1)
    dimension_scores: MockInterviewDimensionScores
    strengths: list[MockInterviewInsightItem] = Field(default_factory=list)
    weaknesses: list[MockInterviewInsightItem] = Field(default_factory=list)
    question_reviews: list[MockInterviewQuestionReview] = Field(default_factory=list)
    follow_up_tasks: list[MockInterviewFollowUpTask] = Field(default_factory=list)
    job_readiness_signal: MockInterviewJobReadinessSignal


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
    question_rubric_json: list[MockInterviewQuestionRubricItem] = Field(default_factory=list)
    answer_text: str | None
    answer_latency_seconds: int | None
    status: str
    evaluation_json: MockInterviewEvaluationJson | None = None
    decision_json: MockInterviewDecisionJson | None = None
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
    plan_json: MockInterviewPlanJson | None = None
    review_json: MockInterviewReviewJson | None = None
    follow_up_tasks_json: list[MockInterviewFollowUpTask] = Field(default_factory=list)
    overall_score: Decimal | None = None
    error_message: str | None
    current_turn: MockInterviewTurnResponse | None = None
    turns: list[MockInterviewTurnResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MockInterviewAnswerSubmitResponse(BaseModel):
    session_id: UUID
    submitted_turn_id: UUID
    submitted_turn_evaluation: MockInterviewEvaluationJson
    next_action: dict[str, object] = Field(default_factory=dict)


class MockInterviewReviewResponse(BaseModel):
    session_id: UUID
    status: str
    overall_score: Decimal | None = None
    review_json: MockInterviewReviewJson | None = None
    follow_up_tasks_json: list[MockInterviewFollowUpTask] = Field(default_factory=list)


class MockInterviewDeleteResponse(BaseModel):
    message: str
