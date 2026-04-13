from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.prompts.tailored_resume import get_tailored_resume_grammar_prompt
from app.schemas.tailored_resume import (
    TailoredResumeGrammarErrorItem,
    TailoredResumeGrammarResponse,
)
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion
from app.services.resume_ai import is_ai_configured


@dataclass(slots=True)
class TailoredResumeGrammarCheckRequest:
    text: str


class TailoredResumeGrammarProvider:
    async def check(
        self, payload: TailoredResumeGrammarCheckRequest
    ) -> TailoredResumeGrammarResponse:
        raise NotImplementedError


class DisabledTailoredResumeGrammarProvider(TailoredResumeGrammarProvider):
    async def check(
        self, payload: TailoredResumeGrammarCheckRequest
    ) -> TailoredResumeGrammarResponse:
        raise ApiException(
            status_code=503,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Tailored resume grammar AI is not configured",
        )


class ConfiguredTailoredResumeGrammarProvider(TailoredResumeGrammarProvider):
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

    async def check(
        self, payload: TailoredResumeGrammarCheckRequest
    ) -> TailoredResumeGrammarResponse:
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
            instructions=get_tailored_resume_grammar_prompt(),
            payload=payload,
            max_tokens=1400,
        )
        return _normalize_grammar_response(payload_json)


def build_tailored_resume_grammar_provider(
    settings: Settings,
) -> TailoredResumeGrammarProvider:
    provider = settings.resume_ai_provider.strip().lower()
    if not is_ai_configured(
        provider=provider,
        base_url=settings.resume_ai_base_url,
        model=settings.resume_ai_model,
        api_key=settings.resume_ai_api_key,
    ):
        return DisabledTailoredResumeGrammarProvider()

    return ConfiguredTailoredResumeGrammarProvider(
        provider=provider,
        base_url=settings.resume_ai_base_url,
        api_key=settings.resume_ai_api_key,
        model=settings.resume_ai_model,
        timeout_seconds=settings.resume_ai_timeout_seconds,
        connect_timeout_seconds=settings.resume_ai_connect_timeout_seconds,
        write_timeout_seconds=settings.resume_ai_write_timeout_seconds,
        read_timeout_seconds=settings.resume_ai_read_timeout_seconds,
        pool_timeout_seconds=settings.resume_ai_pool_timeout_seconds,
    )


async def check_tailored_resume_grammar(
    *,
    text: str,
    settings: Settings,
) -> TailoredResumeGrammarResponse:
    provider = build_tailored_resume_grammar_provider(settings)
    try:
        return await provider.check(TailoredResumeGrammarCheckRequest(text=text))
    except AIClientError as exc:
        raise ApiException(
            status_code=503,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=exc.detail,
        ) from exc


def _normalize_grammar_response(payload: object) -> TailoredResumeGrammarResponse:
    if not isinstance(payload, dict):
        raise AIClientError(
            category="invalid_response_format",
            detail="Tailored resume grammar payload must be a JSON object",
        )

    errors_payload = payload.get("errors", [])
    if not isinstance(errors_payload, list):
        raise AIClientError(
            category="invalid_response_format",
            detail='Tailored resume grammar payload must contain an "errors" array',
        )

    errors: list[TailoredResumeGrammarErrorItem] = []
    for item in errors_payload:
        if not isinstance(item, dict):
            continue
        try:
            errors.append(TailoredResumeGrammarErrorItem.model_validate(item))
        except ValidationError as exc:
            raise AIClientError(
                category="invalid_response_format",
                detail=f"Tailored resume grammar payload validation failed: {exc}",
            ) from exc

    return TailoredResumeGrammarResponse(errors=errors)
