from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.prompts.tailored_resume import get_tailored_resume_rewrite_prompt
from app.schemas.resume import ResumeExperienceBullet
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion

EMPTY_PROVIDER_VALUES = {"", "disabled", "none", "off"}


@dataclass(slots=True)
class AIResumeOptimizationRequest:
    source_resume: dict[str, object]
    job_snapshot: dict[str, object]
    match_report_snapshot: dict[str, object]
    rewrite_tasks: list[dict[str, object]]


class AIResumeOptimizationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    bullets: list[ResumeExperienceBullet] = Field(default_factory=list)


class AIResumeOptimizationUnresolvedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_key: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class AIResumeOptimizationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = ""
    work_experience_items: list[AIResumeOptimizationItem] = Field(default_factory=list)
    project_items: list[AIResumeOptimizationItem] = Field(default_factory=list)
    unresolved_items: list[AIResumeOptimizationUnresolvedItem] = Field(default_factory=list)
    editor_notes: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class AIResumeOptimizationResult:
    provider: str
    model: str | None
    status: str
    payload: AIResumeOptimizationPayload | None = None
    reason: str = ""


class AIResumeOptimizationProvider:
    async def rewrite(
        self, payload: AIResumeOptimizationRequest
    ) -> AIResumeOptimizationResult:
        raise NotImplementedError


class DisabledResumeOptimizationProvider(AIResumeOptimizationProvider):
    async def rewrite(
        self, payload: AIResumeOptimizationRequest
    ) -> AIResumeOptimizationResult:
        return AIResumeOptimizationResult(
            provider="disabled",
            model=None,
            status="skipped",
            reason="Resume optimization AI is disabled",
        )


class ConfiguredResumeOptimizationProvider(AIResumeOptimizationProvider):
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip() if api_key else ""
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def rewrite(
        self, payload: AIResumeOptimizationRequest
    ) -> AIResumeOptimizationResult:
        payload_json = await request_json_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key or None,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
            ),
            instructions=get_tailored_resume_rewrite_prompt(),
            payload=payload,
            max_tokens=2600,
        )
        try:
            parsed = AIResumeOptimizationPayload.model_validate(payload_json)
        except ValidationError as exc:
            raise AIClientError(
                category="invalid_response_format",
                detail=f"Resume optimization AI payload validation failed: {exc}",
            ) from exc
        return AIResumeOptimizationResult(
            provider=self.provider,
            model=self.model,
            status="applied",
            payload=parsed,
        )


def build_resume_optimization_ai_provider(
    settings: Settings | None,
) -> AIResumeOptimizationProvider:
    if settings is None:
        return DisabledResumeOptimizationProvider()

    provider = (settings.resume_ai_provider or "").strip().lower()
    model = (settings.resume_ai_model or "").strip()
    base_url = (settings.resume_ai_base_url or "").strip()
    api_key = (settings.resume_ai_api_key or "").strip() or None
    if provider in EMPTY_PROVIDER_VALUES or not model or not base_url or not api_key:
        return DisabledResumeOptimizationProvider()

    return ConfiguredResumeOptimizationProvider(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=settings.resume_ai_timeout_seconds,
    )
