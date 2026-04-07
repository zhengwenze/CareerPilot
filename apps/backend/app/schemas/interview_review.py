from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MockInterviewReviewType(str, Enum):
    TECHNICAL_ANALYSIS = "technical_analysis"
    PROJECT_EXPERIENCE = "project_experience"
    KNOWLEDGE_FUNDAMENTAL = "knowledge_fundamental"


class InterviewLevelJudgment(str, Enum):
    INCORRECT_OR_INSUFFICIENT = "incorrect_or_insufficient"
    DIRECTIONALLY_CORRECT_BUT_NOT_SYSTEMATIC = "directionally_correct_but_not_systematic"
    BASICALLY_GOOD_BUT_NOT_STRONG_ENOUGH = "basically_good_but_not_strong_enough"
    STRONG_AND_STRUCTURED = "strong_and_structured"
    EXCELLENT_AND_OWNER_LIKE = "excellent_and_owner_like"


class DeepReviewLLMResponse(BaseModel):
    score: float = Field(ge=0, le=10)
    level_judgment: InterviewLevelJudgment
    overall_comment: str = Field(min_length=8, max_length=300)
    strengths: list[str] = Field(min_length=2, max_length=5)
    weaknesses: list[str] = Field(min_length=2, max_length=6)
    missing_framework: list[str] = Field(default_factory=list)
    stronger_answer_outline: list[str] = Field(min_length=3, max_length=7)
    interviewer_concern: str = Field(min_length=8, max_length=200)
    display_comment: str = Field(min_length=10, max_length=300)


class DeepReviewResult(BaseModel):
    status: Literal["pending", "ready", "failed"] = "pending"
    error: str | None = None
    score: float = Field(default=0, ge=0, le=10)
    level_judgment: InterviewLevelJudgment = InterviewLevelJudgment.INCORRECT_OR_INSUFFICIENT
    overall_comment: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_framework: list[str] = Field(default_factory=list)
    stronger_answer_outline: list[str] = Field(default_factory=list)
    interviewer_concern: str = ""
    display_comment: str = ""

    @model_validator(mode="after")
    def validate_ready_state(self) -> DeepReviewResult:
        if self.status != "ready":
            return self
        if len(self.strengths) < 2:
            raise ValueError("ready deep review requires at least 2 strengths")
        if len(self.weaknesses) < 2:
            raise ValueError("ready deep review requires at least 2 weaknesses")
        if len(self.stronger_answer_outline) < 3:
            raise ValueError("ready deep review requires at least 3 stronger_answer_outline items")
        if len(self.overall_comment.strip()) < 8:
            raise ValueError("ready deep review requires overall_comment")
        if len(self.interviewer_concern.strip()) < 8:
            raise ValueError("ready deep review requires interviewer_concern")
        if len(self.display_comment.strip()) < 10:
            raise ValueError("ready deep review requires display_comment")
        return self

    @classmethod
    def pending(cls) -> "DeepReviewResult":
        return cls(status="pending")

    @classmethod
    def failed(cls, message: str = "本次深度点评暂时不可用") -> "DeepReviewResult":
        return cls(status="failed", error=message, display_comment=message)

    @classmethod
    def from_llm_response(
        cls,
        payload: DeepReviewLLMResponse,
        *,
        review_type: MockInterviewReviewType,
    ) -> "DeepReviewResult":
        result = cls(status="ready", **payload.model_dump())
        if review_type == MockInterviewReviewType.TECHNICAL_ANALYSIS and not result.missing_framework:
            raise ValueError("technical_analysis deep review requires missing_framework")
        return result


def coerce_mock_interview_review_type(
    value: str | None,
    *,
    category: str = "",
    intent: str = "",
    text: str = "",
) -> MockInterviewReviewType:
    normalized = (value or "").strip()
    if normalized in {
        MockInterviewReviewType.TECHNICAL_ANALYSIS.value,
        MockInterviewReviewType.PROJECT_EXPERIENCE.value,
        MockInterviewReviewType.KNOWLEDGE_FUNDAMENTAL.value,
    }:
        return MockInterviewReviewType(normalized)

    combined = " ".join([category, intent, text]).lower()
    if any(
        token in combined
        for token in [
            "排查",
            "故障",
            "性能",
            "优化",
            "架构",
            "系统设计",
            "bottleneck",
            "latency",
            "throughput",
            "profil",
            "debug",
            "investigate",
            "root cause",
        ]
    ):
        return MockInterviewReviewType.TECHNICAL_ANALYSIS
    if any(
        token in combined
        for token in [
            "原理",
            "基础",
            "概念",
            "区别",
            "为什么",
            "how does",
            "what is",
            "fundamental",
            "knowledge",
        ]
    ):
        return MockInterviewReviewType.KNOWLEDGE_FUNDAMENTAL
    return MockInterviewReviewType.PROJECT_EXPERIENCE
