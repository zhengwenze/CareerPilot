from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.prompts.tailored_resume import get_tailored_resume_polish_prompt
from app.schemas.tailored_resume import TailoredResumePolishResponse
from app.services.ai_client import (
    AIClientError,
    AIProviderConfig,
    request_text_completion,
)
from app.services.resume_ai import is_ai_configured


@dataclass(slots=True)
class TailoredResumePolishRequestPayload:
    text: str


class TailoredResumePolishProvider:
    async def polish(
        self, payload: TailoredResumePolishRequestPayload
    ) -> TailoredResumePolishResponse:
        raise NotImplementedError


class DisabledTailoredResumePolishProvider(TailoredResumePolishProvider):
    async def polish(
        self, payload: TailoredResumePolishRequestPayload
    ) -> TailoredResumePolishResponse:
        raise ApiException(
            status_code=503,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Tailored resume polish AI is not configured",
        )


class ConfiguredTailoredResumePolishProvider(TailoredResumePolishProvider):
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

    async def polish(
        self, payload: TailoredResumePolishRequestPayload
    ) -> TailoredResumePolishResponse:
        text = await request_text_completion(
            config=AIProviderConfig(
                provider=self.provider,
                base_url=self.base_url,
                api_key=self.api_key or None,
                model=self.model,
                timeout_seconds=self.timeout_seconds,
            ),
            instructions=get_tailored_resume_polish_prompt(),
            payload=payload,
            max_tokens=2600,
        )
        return TailoredResumePolishResponse(text=text)


def build_tailored_resume_polish_provider(
    settings: Settings,
) -> TailoredResumePolishProvider:
    provider = settings.resume_ai_provider.strip().lower()
    if not is_ai_configured(
        provider=provider,
        base_url=settings.resume_ai_base_url,
        model=settings.resume_ai_model,
        api_key=settings.resume_ai_api_key,
    ):
        return DisabledTailoredResumePolishProvider()

    return ConfiguredTailoredResumePolishProvider(
        provider=provider,
        base_url=settings.resume_ai_base_url,
        api_key=settings.resume_ai_api_key,
        model=settings.resume_ai_model,
        timeout_seconds=settings.resume_ai_timeout_seconds,
    )


async def polish_tailored_resume_markdown(
    *,
    text: str,
    settings: Settings,
) -> TailoredResumePolishResponse:
    provider = build_tailored_resume_polish_provider(settings)
    try:
        return await provider.polish(TailoredResumePolishRequestPayload(text=text))
    except AIClientError as exc:
        raise ApiException(
            status_code=503,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=exc.detail,
        ) from exc
