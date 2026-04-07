from __future__ import annotations

import json

from app.core.config import Settings
from app.prompts.mock_interview import (
    get_mock_interview_deep_review_rubric,
    get_mock_interview_deep_review_system_prompt,
    get_mock_interview_deep_review_user_prompt,
)
from app.schemas.interview_review import (
    DeepReviewLLMResponse,
    DeepReviewResult,
    MockInterviewReviewType,
)
from app.services.ai_client import AIProviderConfig, request_text_completion
from app.services.resume_ai import is_ai_configured


def _get_ai_config(settings: Settings, *, model: str | None = None) -> AIProviderConfig:
    return AIProviderConfig(
        provider=settings.interview_ai_provider,
        base_url=settings.interview_ai_base_url,
        api_key=settings.interview_ai_api_key,
        model=model or settings.interview_ai_model_realtime or settings.interview_ai_model,
        timeout_seconds=settings.interview_ai_timeout_seconds,
    )


def _extract_json_snippet(content: str) -> str:
    candidate = content.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            candidate = "\n".join(lines[1:-1]).strip()
    decoder = json.JSONDecoder()
    starts = [index for index, ch in enumerate(candidate) if ch == "{"]
    for start in starts:
        try:
            _, end = decoder.raw_decode(candidate[start:])
            return candidate[start : start + end]
        except json.JSONDecodeError:
            continue
    raise ValueError("Deep review response did not contain valid JSON")


def _parse_json(content: str) -> dict:
    parsed = json.loads(_extract_json_snippet(content))
    if not isinstance(parsed, dict):
        raise ValueError("Deep review response must be a JSON object")
    return parsed


async def review_interview_answer(
    settings: Settings,
    *,
    review_type: MockInterviewReviewType,
    role_summary: str,
    candidate_profile: str,
    question: str,
    answer: str,
    company_or_style: str = "",
) -> DeepReviewResult:
    if not is_ai_configured(
        provider=settings.interview_ai_provider,
        base_url=settings.interview_ai_base_url,
        model=settings.interview_ai_model_realtime or settings.interview_ai_model,
        api_key=settings.interview_ai_api_key,
    ):
        return DeepReviewResult.failed()

    try:
        content = await request_text_completion(
            config=_get_ai_config(settings),
            instructions=get_mock_interview_deep_review_system_prompt(),
            payload={
                "prompt": get_mock_interview_deep_review_user_prompt().format(
                    review_type=review_type.value,
                    role_summary=role_summary,
                    company_or_style=company_or_style,
                    candidate_profile=candidate_profile,
                    rubric=get_mock_interview_deep_review_rubric(review_type),
                    question=question,
                    answer=answer,
                )
            },
            max_tokens=1200,
        )
        parsed = _parse_json(content)
        llm_response = DeepReviewLLMResponse.model_validate(parsed)
        return DeepReviewResult.from_llm_response(llm_response, review_type=review_type)
    except Exception:
        return DeepReviewResult.failed()
