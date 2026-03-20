from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.prompts.mock_interview import render_mock_interview_prompt
from app.schemas.mock_interview import (
    MockInterviewDecisionJson,
    MockInterviewEvaluationJson,
    MockInterviewPlanJson,
    MockInterviewReviewJson,
)
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion


@dataclass(slots=True)
class AIInterviewPlanRequest:
    resume_snapshot: dict[str, object]
    job_snapshot: dict[str, object]
    match_report_snapshot: dict[str, object]
    optimization_snapshot: dict[str, object]
    session_mode: str
    constraints: dict[str, int]


@dataclass(slots=True)
class AIInterviewEvaluationRequest:
    session_context: dict[str, object]
    current_question: dict[str, object]
    conversation_history: list[dict[str, object]]
    candidate_answer: dict[str, object]


@dataclass(slots=True)
class AIInterviewDecisionRequest:
    session_context: dict[str, object]
    current_question: dict[str, object]
    conversation_history: list[dict[str, object]]
    candidate_answer: dict[str, object]
    evaluation_json: dict[str, object]
    remaining_question_topics: list[str]
    constraints: dict[str, object]


@dataclass(slots=True)
class AIInterviewReviewRequest:
    session_context: dict[str, object]
    match_report_snapshot: dict[str, object]
    transcript: list[dict[str, object]]


def _schema_json(model_cls: type[BaseModel]) -> str:
    return json.dumps(model_cls.model_json_schema(), ensure_ascii=False, indent=2)


def _build_repair_instructions(
    *,
    template_name: str,
    contract_json_schema: str,
    **variables: str,
) -> str:
    base_instructions = render_mock_interview_prompt(
        template_name,
        contract_json_schema=contract_json_schema,
        **variables,
    )
    return (
        f"{base_instructions}\n\n"
        "Your previous response violated the JSON contract.\n"
        "Regenerate the full response as strict JSON only.\n"
        "Do not add markdown, explanations, or extra keys."
    )


class AIMockInterviewProvider:
    async def plan(self, payload: AIInterviewPlanRequest) -> MockInterviewPlanJson:
        raise NotImplementedError

    async def evaluate_turn(
        self,
        payload: AIInterviewEvaluationRequest,
    ) -> MockInterviewEvaluationJson:
        raise NotImplementedError

    async def decide_turn(
        self,
        payload: AIInterviewDecisionRequest,
    ) -> MockInterviewDecisionJson:
        raise NotImplementedError

    async def review(self, payload: AIInterviewReviewRequest) -> MockInterviewReviewJson:
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

    async def plan(self, payload: AIInterviewPlanRequest) -> MockInterviewPlanJson:
        contract_json_schema = _schema_json(MockInterviewPlanJson)
        return await self._validate_with_repair(
            instructions=render_mock_interview_prompt(
                "interview_plan_system",
                contract_json_schema=contract_json_schema,
                max_questions=str(payload.constraints.get("max_questions", 6)),
                max_follow_ups_per_question=str(
                    payload.constraints.get("max_follow_ups_per_question", 1)
                ),
            ),
            repair_instructions=_build_repair_instructions(
                template_name="interview_plan_system",
                contract_json_schema=contract_json_schema,
                max_questions=str(payload.constraints.get("max_questions", 6)),
                max_follow_ups_per_question=str(
                    payload.constraints.get("max_follow_ups_per_question", 1)
                ),
            ),
            payload=payload,
            model_cls=MockInterviewPlanJson,
            max_tokens=2200,
        )

    async def evaluate_turn(
        self,
        payload: AIInterviewEvaluationRequest,
    ) -> MockInterviewEvaluationJson:
        contract_json_schema = _schema_json(MockInterviewEvaluationJson)
        return await self._validate_with_repair(
            instructions=render_mock_interview_prompt(
                "interview_turn_evaluator",
                contract_json_schema=contract_json_schema,
            ),
            repair_instructions=_build_repair_instructions(
                template_name="interview_turn_evaluator",
                contract_json_schema=contract_json_schema,
            ),
            payload=payload,
            model_cls=MockInterviewEvaluationJson,
            max_tokens=1200,
        )

    async def decide_turn(
        self,
        payload: AIInterviewDecisionRequest,
    ) -> MockInterviewDecisionJson:
        contract_json_schema = _schema_json(MockInterviewDecisionJson)
        return await self._validate_with_repair(
            instructions=render_mock_interview_prompt(
                "interview_followup_decider",
                contract_json_schema=contract_json_schema,
            ),
            repair_instructions=_build_repair_instructions(
                template_name="interview_followup_decider",
                contract_json_schema=contract_json_schema,
            ),
            payload=payload,
            model_cls=MockInterviewDecisionJson,
            max_tokens=900,
        )

    async def review(self, payload: AIInterviewReviewRequest) -> MockInterviewReviewJson:
        contract_json_schema = _schema_json(MockInterviewReviewJson)
        return await self._validate_with_repair(
            instructions=render_mock_interview_prompt(
                "interview_final_review",
                contract_json_schema=contract_json_schema,
            ),
            repair_instructions=_build_repair_instructions(
                template_name="interview_final_review",
                contract_json_schema=contract_json_schema,
            ),
            payload=payload,
            model_cls=MockInterviewReviewJson,
            max_tokens=2200,
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
