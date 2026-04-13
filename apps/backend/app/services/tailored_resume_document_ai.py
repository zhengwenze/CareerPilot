from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import Settings
from app.prompts.tailored_resume import get_tailored_resume_full_document_prompt
from app.schemas.tailored_resume import TailoredResumeDocument
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion
from app.services.resume_ai import is_ai_configured


@dataclass(slots=True)
class AITailoredResumeDocumentRequest:
    output_language: str
    job_description: str
    job_keywords: list[str]
    original_resume_json: dict[str, object]
    original_resume_markdown: str
    optimization_level: str


@dataclass(slots=True)
class AITailoredResumeDocumentResult:
    provider: str
    model: str | None
    status: str
    payload: TailoredResumeDocument | None = None
    reason: str = ""


class AITailoredResumeDocumentProvider:
    async def generate(
        self, payload: AITailoredResumeDocumentRequest
    ) -> AITailoredResumeDocumentResult:
        raise NotImplementedError


class DisabledTailoredResumeDocumentProvider(AITailoredResumeDocumentProvider):
    async def generate(
        self, payload: AITailoredResumeDocumentRequest
    ) -> AITailoredResumeDocumentResult:
        del payload
        return AITailoredResumeDocumentResult(
            provider="disabled",
            model=None,
            status="skipped",
            reason="Tailored resume document AI is disabled",
        )


class ConfiguredTailoredResumeDocumentProvider(AITailoredResumeDocumentProvider):
    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_seconds: int,
        connect_timeout_seconds: int | None = None,
        write_timeout_seconds: int | None = None,
        read_timeout_seconds: int | None = None,
        pool_timeout_seconds: int | None = None,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip() if api_key else ""
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.connect_timeout_seconds = connect_timeout_seconds
        self.write_timeout_seconds = write_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self.pool_timeout_seconds = pool_timeout_seconds

    async def generate(
        self, payload: AITailoredResumeDocumentRequest
    ) -> AITailoredResumeDocumentResult:
        payload_json = await request_json_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key or None,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
                connect_timeout_seconds=self.connect_timeout_seconds,
                write_timeout_seconds=self.write_timeout_seconds,
                read_timeout_seconds=self.read_timeout_seconds,
                pool_timeout_seconds=self.pool_timeout_seconds,
            ),
            instructions=get_tailored_resume_full_document_prompt(),
            payload=payload,
            max_tokens=5200,
        )
        try:
            parsed = TailoredResumeDocument.model_validate(payload_json)
        except ValidationError as exc:
            raise AIClientError(
                category="invalid_response_format",
                detail=f"Tailored resume document payload validation failed: {exc}",
            ) from exc

        return AITailoredResumeDocumentResult(
            provider=self.provider,
            model=self.model,
            status="applied",
            payload=parsed,
        )


def build_tailored_resume_document_ai_provider(
    settings: Settings | None,
) -> AITailoredResumeDocumentProvider:
    if settings is None:
        return DisabledTailoredResumeDocumentProvider()

    provider = (settings.resume_ai_provider or "").strip().lower()
    model = (settings.resume_ai_model or "").strip()
    base_url = (settings.resume_ai_base_url or "").strip()
    api_key = (settings.resume_ai_api_key or "").strip() or None
    if not is_ai_configured(
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=api_key,
    ):
        return DisabledTailoredResumeDocumentProvider()

    return ConfiguredTailoredResumeDocumentProvider(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=settings.resume_ai_timeout_seconds,
        connect_timeout_seconds=settings.resume_ai_connect_timeout_seconds,
        write_timeout_seconds=settings.resume_ai_write_timeout_seconds,
        read_timeout_seconds=settings.resume_ai_read_timeout_seconds,
        pool_timeout_seconds=settings.resume_ai_pool_timeout_seconds,
    )
