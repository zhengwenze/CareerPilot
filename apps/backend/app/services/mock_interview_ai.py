from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion

PLANNER_INSTRUCTIONS = """
You are the interview planner for a job-specific mock interview.

Build a compact interview plan from:
- resume_snapshot
- job_snapshot
- match_report_snapshot
- optional optimization_snapshot

Hard constraints:
- Output strict JSON only.
- Stay grounded in the provided resume, job, and match report.
- Do not invent employers, projects, metrics, technologies, or achievements.
- Prefer interview_blueprint_json.question_pack and focus_areas when available.
- Prioritize weak areas from gap_json and tailoring_plan_json.must_add_evidence.
- Produce at most 6 main questions.
- Each main question can have at most 1 follow-up rule.
- Keep questions concise and suitable for a text-only interview.
""".strip()

PLANNER_REPAIR_INSTRUCTIONS = """
Your previous planner JSON was invalid.

Regenerate the full interview plan.
- Output strict JSON only.
- Keep the same schema.
- Do not invent candidate evidence.
""".strip()

TURN_INSTRUCTIONS = """
You are the turn orchestrator for a structured mock interview.

Evaluate the candidate answer and choose exactly one next action:
- follow_up
- next_question
- finish_and_review

Hard constraints:
- Output strict JSON only.
- Do not invent missing candidate evidence.
- Use only the provided answer and context.
- If the answer is relevant but vague, prefer one focused follow-up.
- If the answer is off-topic or already exhausted, move on.
- Do not ask more than one follow-up for the same main question.
""".strip()

TURN_REPAIR_INSTRUCTIONS = """
Your previous turn-evaluation JSON was invalid.

Regenerate the full JSON object.
- Output strict JSON only.
- Keep the same schema.
- Choose exactly one next action.
""".strip()

REVIEW_INSTRUCTIONS = """
You are the final reviewer for a structured mock interview.

Produce a compact but actionable review.

Hard constraints:
- Output strict JSON only.
- Ground all conclusions in the transcript and match_report_snapshot.
- Do not invent candidate experience or unrelated improvement tasks.
- The review must help improve both interview answers and resume evidence.
""".strip()

REVIEW_REPAIR_INSTRUCTIONS = """
Your previous review JSON was invalid.

Regenerate the full JSON object.
- Output strict JSON only.
- Keep the same schema.
- Do not invent evidence.
""".strip()


@dataclass(slots=True)
class AIInterviewPlanRequest:
    resume_snapshot: dict[str, object]
    job_snapshot: dict[str, object]
    match_report_snapshot: dict[str, object]
    optimization_snapshot: dict[str, object]
    session_mode: str
    constraints: dict[str, int]


@dataclass(slots=True)
class AIInterviewTurnRequest:
    session_context: dict[str, object]
    current_question: dict[str, object]
    conversation_history: list[dict[str, object]]
    candidate_answer: dict[str, object]
    remaining_question_topics: list[str]
    constraints: dict[str, int]


@dataclass(slots=True)
class AIInterviewReviewRequest:
    session_context: dict[str, object]
    match_report_snapshot: dict[str, object]
    transcript: list[dict[str, object]]


class InterviewPlanFocusArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    priority: str = "medium"


class InterviewPlanRubricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(min_length=1)
    weight: int = Field(ge=1)
    criteria: str = Field(min_length=1)


class InterviewPlannedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_index: int = Field(ge=1)
    topic: str = Field(min_length=1)
    source: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    follow_up_rule: str | None = None
    rubric: list[InterviewPlanRubricItem] = Field(default_factory=list)


class InterviewPlanEndingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_questions: int = Field(ge=1)
    max_follow_ups_per_question: int = Field(ge=0)


class InterviewPlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_summary: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    target_role: str | None = None
    focus_areas: list[InterviewPlanFocusArea] = Field(default_factory=list)
    question_plan: list[InterviewPlannedQuestion] = Field(default_factory=list)
    ending_rule: InterviewPlanEndingRule


class InterviewTurnEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension_scores: dict[str, int] = Field(default_factory=dict)
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)


class InterviewDecisionQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    intent: str = Field(min_length=1)


class InterviewTurnDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["follow_up", "next_question", "finish_and_review"]
    reason: str = Field(min_length=1)
    next_question: InterviewDecisionQuestion | None = None


class InterviewTurnPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation: InterviewTurnEvaluation
    decision: InterviewTurnDecision


class InterviewReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    severity: str | None = None


class InterviewQuestionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_text: str = Field(min_length=1)
    what_went_well: str = Field(min_length=1)
    what_was_missing: str = Field(min_length=1)
    better_answer_direction: str = Field(min_length=1)


class InterviewFollowUpTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    target_section: str = "work_experience_or_projects"
    source: str = "mock_interview_review"


class InterviewReadinessSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class InterviewReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_score: float = Field(ge=0.0, le=100.0)
    overall_summary: str = Field(min_length=1)
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    strengths: list[InterviewReviewItem] = Field(default_factory=list)
    weaknesses: list[InterviewReviewItem] = Field(default_factory=list)
    question_reviews: list[InterviewQuestionReview] = Field(default_factory=list)
    follow_up_tasks: list[InterviewFollowUpTask] = Field(default_factory=list)
    job_readiness_signal: InterviewReadinessSignal


class AIMockInterviewProvider:
    async def plan(self, payload: AIInterviewPlanRequest) -> InterviewPlanPayload:
        raise NotImplementedError

    async def evaluate_turn(self, payload: AIInterviewTurnRequest) -> InterviewTurnPayload:
        raise NotImplementedError

    async def review(self, payload: AIInterviewReviewRequest) -> InterviewReviewPayload:
        raise NotImplementedError


class ConfiguredAIMockInterviewProvider(AIMockInterviewProvider):
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def _request(
        self,
        *,
        instructions: str,
        payload: object,
        max_tokens: int,
    ) -> dict[str, object]:
        return await request_json_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
            ),
            instructions=instructions,
            payload=payload,
            max_tokens=max_tokens,
        )

    async def _validate_with_repair(
        self,
        *,
        instructions: str,
        repair_instructions: str,
        payload: object,
        model_cls: type[BaseModel],
        max_tokens: int,
    ) -> BaseModel:
        response_json = await self._request(
            instructions=instructions,
            payload=payload,
            max_tokens=max_tokens,
        )
        try:
            return model_cls.model_validate(response_json)
        except ValidationError:
            repaired_json = await self._request(
                instructions=repair_instructions,
                payload={
                    "original_request": payload,
                    "previous_invalid_response": response_json,
                },
                max_tokens=max_tokens,
            )
            try:
                return model_cls.model_validate(repaired_json)
            except ValidationError as exc:
                raise AIClientError(
                    category="invalid_response_format",
                    detail=f"Mock interview AI payload validation failed: {exc}",
                ) from exc

    async def plan(self, payload: AIInterviewPlanRequest) -> InterviewPlanPayload:
        return await self._validate_with_repair(
            instructions=PLANNER_INSTRUCTIONS,
            repair_instructions=PLANNER_REPAIR_INSTRUCTIONS,
            payload=payload,
            model_cls=InterviewPlanPayload,
            max_tokens=1800,
        )

    async def evaluate_turn(self, payload: AIInterviewTurnRequest) -> InterviewTurnPayload:
        return await self._validate_with_repair(
            instructions=TURN_INSTRUCTIONS,
            repair_instructions=TURN_REPAIR_INSTRUCTIONS,
            payload=payload,
            model_cls=InterviewTurnPayload,
            max_tokens=1200,
        )

    async def review(self, payload: AIInterviewReviewRequest) -> InterviewReviewPayload:
        return await self._validate_with_repair(
            instructions=REVIEW_INSTRUCTIONS,
            repair_instructions=REVIEW_REPAIR_INSTRUCTIONS,
            payload=payload,
            model_cls=InterviewReviewPayload,
            max_tokens=1800,
        )


def build_mock_interview_ai_provider(settings: Settings) -> AIMockInterviewProvider:
    provider = settings.interview_ai_provider.strip().lower()
    if provider != "minimax":
        raise ValueError("INTERVIEW_AI_PROVIDER must be minimax for mock interviews")
    if not settings.interview_ai_base_url.strip():
        raise ValueError("INTERVIEW_AI_BASE_URL is required for mock interviews")
    if not settings.interview_ai_api_key or not settings.interview_ai_api_key.strip():
        raise ValueError("INTERVIEW_AI_API_KEY is required for mock interviews")
    if not settings.interview_ai_model or not settings.interview_ai_model.strip():
        raise ValueError("INTERVIEW_AI_MODEL is required for mock interviews")

    return ConfiguredAIMockInterviewProvider(
        provider=provider,
        base_url=settings.interview_ai_base_url,
        api_key=settings.interview_ai_api_key,
        model=settings.interview_ai_model,
        timeout_seconds=settings.interview_ai_timeout_seconds,
    )
