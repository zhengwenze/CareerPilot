from __future__ import annotations
import asyncio
import json
import logging
from dataclasses import asdict, dataclass, is_dataclass
from json import JSONDecodeError
import os
import anthropic

logger = logging.getLogger(__name__)
RETRYABLE_AI_ERROR_CATEGORIES = {"timeout", "connection_error"}
MAX_AI_REQUEST_RETRIES = 1
AI_RETRY_BACKOFF_SECONDS = 0.8
DEFAULT_MINIMAX_ANTHROPIC_BASE_URL = "https://api.minimaxi.com/anthropic"


@dataclass(frozen=True, slots=True)
class AIProviderConfig:
    provider: str
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: int


class AIClientError(Exception):
    def __init__(self, *, category: str, detail: str) -> None:
        super().__init__(detail)
        self.category = category
        self.detail = detail


async def request_json_completion(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
    max_tokens: int = 4000,
) -> dict[str, object]:
    try:
        total_attempts = 1 + MAX_AI_REQUEST_RETRIES
        logger.info(
            "AI JSON completion started provider=%s model=%s "
            "base_url=%s timeout_seconds=%s payload_chars=%s attempts=%s",
            config.provider,
            config.model,
            config.base_url,
            config.timeout_seconds,
            len(_serialize_payload(payload)),
            total_attempts,
        )
        content = ""
        for attempt in range(1, total_attempts + 1):
            try:
                content = await _request_anthropic_text(
                    config=config,
                    instructions=instructions,
                    payload=payload,
                    max_tokens=max_tokens,
                )
                if attempt > 1:
                    logger.info(
                        "AI JSON completion recovered after retry provider=%s model=%s attempt=%s",
                        config.provider,
                        config.model,
                        attempt,
                    )
                break
            except AIClientError as exc:
                is_retryable = exc.category in RETRYABLE_AI_ERROR_CATEGORIES
                has_next_attempt = attempt < total_attempts
                if not is_retryable or not has_next_attempt:
                    raise
                backoff_seconds = AI_RETRY_BACKOFF_SECONDS * attempt
                logger.warning(
                    "AI JSON completion transient failure provider=%s model=%s "
                    "category=%s attempt=%s/%s retry_in=%.2fs",
                    config.provider,
                    config.model,
                    exc.category,
                    attempt,
                    total_attempts,
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)
        json_content = _extract_json_object(content)
        logger.info(
            "AI JSON object extracted provider=%s model=%s content_chars=%s json_chars=%s",
            config.provider,
            config.model,
            len(content),
            len(json_content),
        )
        parsed = json.loads(json_content)
        if not isinstance(parsed, dict):
            raise AIClientError(
                category="invalid_response_format",
                detail=f"AI response JSON root must be an object, got {type(parsed).__name__}",
            )
        logger.info(
            "AI JSON completion parsed successfully provider=%s model=%s top_level_type=%s",
            config.provider,
            config.model,
            type(parsed).__name__,
        )
        return parsed
    except AIClientError:
        logger.exception(
            "AI JSON completion failed provider=%s model=%s",
            config.provider,
            config.model,
        )
        raise
    except JSONDecodeError as exc:
        logger.exception(
            "AI JSON decoding failed provider=%s model=%s",
            config.provider,
            config.model,
        )
        raise AIClientError(
            category="json_decode_error",
            detail=f"AI response contained invalid JSON: {exc.msg}",
        ) from exc
    except ValueError as exc:
        logger.exception(
            "AI response format validation failed provider=%s model=%s",
            config.provider,
            config.model,
        )
        raise AIClientError(
            category="invalid_response_format",
            detail=str(exc),
        ) from exc


async def _request_anthropic_text(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
    max_tokens: int,
) -> str:
    logger.info(
        "AI Anthropic request building provider=%s model=%s "
        "base_url=%s has_api_key=%s timeout_seconds=%s max_tokens=%s",
        config.provider,
        config.model,
        _resolve_base_url(config),
        bool(config.api_key),
        config.timeout_seconds,
        max_tokens,
    )
    client = anthropic.AsyncAnthropic(**_build_anthropic_client_kwargs(config))

    try:
        logger.info(
            "AI Anthropic request sending provider=%s model=%s",
            config.provider,
            config.model,
        )
        response = await client.messages.create(
            model=config.model,
            max_tokens=max_tokens,
            system=instructions,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": _serialize_payload(payload),
                        }
                    ],
                }
            ],
        )
        logger.info(
            "AI Anthropic response received provider=%s model=%s stop_reason=%s content_items=%s",
            config.provider,
            config.model,
            getattr(response, "stop_reason", None),
            len(getattr(response, "content", []) or []),
        )
    except anthropic.AuthenticationError as exc:
        raise AIClientError(
            category="auth_error",
            detail=f"AI authentication failed (401): {exc}",
        ) from exc
    except anthropic.PermissionDeniedError as exc:
        raise AIClientError(
            category="permission_error",
            detail=f"AI permission denied (403): {exc}",
        ) from exc
    except anthropic.APITimeoutError as exc:
        raise AIClientError(
            category="timeout",
            detail=f"AI request timed out: {exc}",
        ) from exc
    except anthropic.APIStatusError as exc:
        raise AIClientError(
            category=f"http_{exc.status_code}",
            detail=f"AI request failed with HTTP {exc.status_code}: {exc}",
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise AIClientError(
            category="connection_error",
            detail=f"AI connection failed: {exc}",
        ) from exc
    except anthropic.APIResponseValidationError as exc:
        raise AIClientError(
            category="invalid_response_format",
            detail=f"AI response schema validation failed: {exc}",
        ) from exc
    except anthropic.AnthropicError as exc:
        raise AIClientError(
            category="provider_error",
            detail=f"AI provider error: {exc}",
        ) from exc

    return _anthropic_response_text(response)


def _serialize_payload(payload: object) -> str:
    if is_dataclass(payload):
        payload = asdict(payload)
    return json.dumps(payload, ensure_ascii=False)


def _extract_json_object(content: str) -> str:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = _strip_markdown_code_fence(candidate)

    decoder = json.JSONDecoder()
    starts = [index for index, ch in enumerate(candidate) if ch == "{"]
    for start in starts:
        try:
            _, end = decoder.raw_decode(candidate[start:])
            return candidate[start : start + end]
        except JSONDecodeError:
            continue

    raise ValueError("AI response did not contain a valid JSON object")


def _strip_markdown_code_fence(content: str) -> str:
    lines = content.splitlines()
    if len(lines) < 2:
        return content
    if not lines[0].lstrip().startswith("```"):
        return content

    end_index = None
    for index in range(len(lines) - 1, 0, -1):
        if lines[index].strip().startswith("```"):
            end_index = index
            break
    if end_index is None or end_index <= 0:
        return content
    return "\n".join(lines[1:end_index]).strip()


def _anthropic_response_text(response: object) -> str:
    content = getattr(response, "content", None)
    if not isinstance(content, list):
        raise ValueError("AI response did not contain content items")

    chunks: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str):
                chunks.append(text)

    if not chunks:
        raise ValueError("AI response did not contain assistant text")

    logger.info(
        "AI Anthropic text extracted content_items=%s text_chunks=%s text_chars=%s",
        len(content),
        len(chunks),
        len("".join(chunks)),
    )

    return "".join(chunks)


def _resolve_base_url(config: AIProviderConfig) -> str:
    configured = (config.base_url or "").strip()
    if configured:
        return configured
    env_base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()
    if env_base_url:
        return env_base_url
    return DEFAULT_MINIMAX_ANTHROPIC_BASE_URL


def _build_anthropic_client_kwargs(config: AIProviderConfig) -> dict[str, object]:
    provider = (config.provider or "").strip().lower()
    kwargs: dict[str, object] = {
        "base_url": _resolve_base_url(config),
        "timeout": config.timeout_seconds,
    }
    if provider == "minimax":
        kwargs["auth_token"] = config.api_key
    else:
        kwargs["api_key"] = config.api_key
    return kwargs
