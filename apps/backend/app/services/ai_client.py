from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass, is_dataclass
from json import JSONDecodeError
from time import perf_counter
from urllib.parse import SplitResult, urlsplit, urlunsplit

import anthropic
import httpx

logger = logging.getLogger(__name__)
RETRYABLE_HTTP_STATUS_CATEGORIES = {"http_502", "http_503", "http_504"}
RETRYABLE_CONNECTION_ERROR_MARKERS = (
    "remote end closed connection without response",
    "connection reset",
    "server disconnected",
)
UPSTREAM_DISCONNECT_ERROR_MARKERS = RETRYABLE_CONNECTION_ERROR_MARKERS + (
    "unexpected_eof_while_reading",
    "eof occurred in violation of protocol",
)
MAX_AI_REQUEST_RETRIES = 1
AI_RETRY_BACKOFF_SECONDS = 0.8
MIN_RETRY_BUDGET_SECONDS = 5.0
RAW_RESPONSE_PREVIEW_LIMIT = 1000
DEFAULT_MINIMAX_ANTHROPIC_BASE_URL = "https://api.minimaxi.com/anthropic"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_CODEX2GPT_BASE_URL = "http://127.0.0.1:18100/v1"
DEFAULT_CODEX2GPT_CLIENT_ID = "career-pilot-backend"
DEFAULT_CODEX2GPT_BUSINESS_KEY = "career-pilot"


@dataclass(frozen=True, slots=True)
class AIProviderConfig:
    provider: str
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class AIAttemptContext:
    retry_count: int
    attempt_index: int
    attempt_total: int
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class AICompletionResponse:
    text: str
    response_text_source: str


class AIClientError(Exception):
    def __init__(self, *, category: str, detail: str) -> None:
        super().__init__(detail)
        self.category = category
        self.detail = detail


async def request_text_completion(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
    max_tokens: int = 4000,
    retry_count_override: int | None = None,
    total_timeout_budget_seconds: float | None = None,
) -> str:
    try:
        completion = await _request_completion_with_retries(
            config=config,
            instructions=instructions,
            payload=payload,
            max_tokens=max_tokens,
            retry_count_override=retry_count_override,
            total_timeout_budget_seconds=total_timeout_budget_seconds,
            completion_kind="text",
        )
        normalized = completion.text.strip()
        if not normalized:
            raise AIClientError(
                category="invalid_response_format",
                detail="AI response did not contain text content",
            )
        logger.info(
            "AI text completion parsed successfully provider=%s model=%s text_chars=%s response_text_source=%s",
            config.provider,
            config.model,
            len(normalized),
            completion.response_text_source,
        )
        return normalized
    except AIClientError:
        logger.exception(
            "AI text completion failed provider=%s model=%s",
            config.provider,
            config.model,
        )
        raise


async def request_json_completion(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
    max_tokens: int = 4000,
    retry_count_override: int | None = None,
    total_timeout_budget_seconds: float | None = None,
) -> dict[str, object]:
    try:
        completion = await _request_completion_with_retries(
            config=config,
            instructions=instructions,
            payload=payload,
            max_tokens=max_tokens,
            retry_count_override=retry_count_override,
            total_timeout_budget_seconds=total_timeout_budget_seconds,
            completion_kind="json",
        )
        json_content = _extract_json_object(completion.text)
        logger.info(
            "AI JSON object extracted provider=%s model=%s content_chars=%s json_chars=%s response_text_source=%s",
            config.provider,
            config.model,
            len(completion.text),
            len(json_content),
            completion.response_text_source,
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


async def _request_provider_text(
    *,
    config: AIProviderConfig,
    instructions: str,
    serialized_payload: str,
    max_tokens: int,
    attempt_context: AIAttemptContext,
) -> AICompletionResponse:
    provider = (config.provider or "").strip().lower()
    if provider == "ollama":
        return await _request_ollama_text(
            config=config,
            instructions=instructions,
            serialized_payload=serialized_payload,
            max_tokens=max_tokens,
            attempt_context=attempt_context,
        )
    if provider == "codex2gpt":
        return await _request_codex2gpt_text(
            config=config,
            instructions=instructions,
            serialized_payload=serialized_payload,
            max_tokens=max_tokens,
            attempt_context=attempt_context,
        )
    return await _request_anthropic_text(
        config=config,
        instructions=instructions,
        serialized_payload=serialized_payload,
        max_tokens=max_tokens,
        attempt_context=attempt_context,
    )


async def _request_completion_with_retries(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
    max_tokens: int,
    retry_count_override: int | None,
    total_timeout_budget_seconds: float | None,
    completion_kind: str,
) -> AICompletionResponse:
    serialized_payload = _serialize_payload(payload)
    total_attempts = _resolve_total_attempts(retry_count_override)
    retry_count = max(0, total_attempts - 1)
    deadline = (
        perf_counter() + float(total_timeout_budget_seconds)
        if total_timeout_budget_seconds is not None
        else None
    )

    logger.info(
        "AI %s completion started provider=%s model=%s base_url=%s timeout_seconds=%s payload_chars=%s attempts=%s total_timeout_budget_seconds=%s",
        completion_kind,
        config.provider,
        config.model,
        config.base_url,
        config.timeout_seconds,
        len(serialized_payload),
        total_attempts,
        total_timeout_budget_seconds,
    )

    for attempt_index in range(1, total_attempts + 1):
        timeout_seconds = _resolve_attempt_timeout_seconds(
            config_timeout_seconds=config.timeout_seconds,
            deadline=deadline,
        )
        attempt_context = AIAttemptContext(
            retry_count=retry_count,
            attempt_index=attempt_index,
            attempt_total=total_attempts,
            timeout_seconds=timeout_seconds,
        )
        try:
            response = await _request_provider_text(
                config=_config_with_timeout(config, timeout_seconds),
                instructions=instructions,
                serialized_payload=serialized_payload,
                max_tokens=max_tokens,
                attempt_context=attempt_context,
            )
            if attempt_index > 1:
                logger.info(
                    "AI %s completion recovered after retry provider=%s model=%s attempt=%s/%s",
                    completion_kind,
                    config.provider,
                    config.model,
                    attempt_index,
                    total_attempts,
                )
            return response
        except AIClientError as exc:
            _log_attempt_exception(
                provider=config.provider,
                model=config.model,
                attempt_context=attempt_context,
                exc=exc,
            )
            if attempt_index >= total_attempts or not _is_retryable_ai_error(exc):
                raise
            backoff_seconds = AI_RETRY_BACKOFF_SECONDS * attempt_index
            if not _can_retry_within_budget(deadline=deadline, backoff_seconds=backoff_seconds):
                logger.warning(
                    "AI %s completion retry skipped due to exhausted budget provider=%s model=%s category=%s attempt=%s/%s backoff_seconds=%.2f",
                    completion_kind,
                    config.provider,
                    config.model,
                    exc.category,
                    attempt_index,
                    total_attempts,
                    backoff_seconds,
                )
                raise
            logger.warning(
                "AI %s completion transient failure provider=%s model=%s category=%s attempt=%s/%s retry_in=%.2fs",
                completion_kind,
                config.provider,
                config.model,
                exc.category,
                attempt_index,
                total_attempts,
                backoff_seconds,
            )
            await asyncio.sleep(backoff_seconds)

    raise AIClientError(category="provider_error", detail="AI completion exhausted attempts")


async def _request_anthropic_text(
    *,
    config: AIProviderConfig,
    instructions: str,
    serialized_payload: str,
    max_tokens: int,
    attempt_context: AIAttemptContext,
) -> AICompletionResponse:
    base_url = _resolve_base_url(config)
    endpoint = f"{base_url.rstrip('/')}/messages"
    request_body = {
        "model": config.model,
        "max_tokens": max_tokens,
        "system": instructions,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": serialized_payload}],
            }
        ],
    }
    _log_request_attempt(
        provider=config.provider,
        model=config.model,
        endpoint=endpoint,
        stream=False,
        request_body=request_body,
        message_values=[instructions, serialized_payload],
        attempt_context=attempt_context,
    )
    client = anthropic.AsyncAnthropic(**_build_anthropic_client_kwargs(config))

    try:
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
                            "text": serialized_payload,
                        }
                    ],
                }
            ],
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
            detail=f"AI request timed out after {config.timeout_seconds:g}s while waiting for upstream response",
        ) from exc
    except anthropic.APIStatusError as exc:
        _log_response_attempt(
            provider=config.provider,
            model=config.model,
            endpoint=endpoint,
            http_status_code=exc.status_code,
            raw_response_preview=_build_response_preview(
                getattr(getattr(exc, "response", None), "text", None)
                or getattr(exc, "body", None)
                or str(exc)
            ),
            response_text_source="none",
            attempt_context=attempt_context,
        )
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

    raw_response_preview = _build_response_preview(_safe_json_dumps(_anthropic_response_payload(response)))
    try:
        text = _anthropic_response_text(response)
    except ValueError as exc:
        _log_response_attempt(
            provider=config.provider,
            model=config.model,
            endpoint=endpoint,
            http_status_code=200,
            raw_response_preview=raw_response_preview,
            response_text_source="none",
            attempt_context=attempt_context,
        )
        raise AIClientError(
            category="invalid_response_format",
            detail=str(exc),
        ) from exc

    _log_response_attempt(
        provider=config.provider,
        model=config.model,
        endpoint=endpoint,
        http_status_code=200,
        raw_response_preview=raw_response_preview,
        response_text_source="content[].text",
        attempt_context=attempt_context,
    )
    return AICompletionResponse(
        text=text,
        response_text_source="content[].text",
    )


async def _request_ollama_text(
    *,
    config: AIProviderConfig,
    instructions: str,
    serialized_payload: str,
    max_tokens: int,
    attempt_context: AIAttemptContext,
) -> AICompletionResponse:
    request_body = {
        "model": config.model,
        "stream": False,
        "keep_alive": "10m",
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": serialized_payload},
        ],
        "options": {"num_predict": max_tokens},
    }
    base_url = _resolve_ollama_base_url(config)
    endpoint = f"{base_url}/api/chat"
    _log_request_attempt(
        provider=config.provider,
        model=config.model,
        endpoint=endpoint,
        stream=False,
        request_body=request_body,
        message_values=[instructions, serialized_payload],
        attempt_context=attempt_context,
    )

    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                endpoint,
                json=request_body,
            )
            response.raise_for_status()
            response_json = response.json()
    except httpx.TimeoutException as exc:
        raise AIClientError(
            category="timeout",
            detail=f"AI request timed out after {config.timeout_seconds:g}s while waiting for upstream response",
        ) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        detail = exc.response.text.strip() or str(exc)
        category = _classify_http_error_category(
            provider=config.provider,
            status_code=status_code,
            detail=detail,
        )
        _log_response_attempt(
            provider=config.provider,
            model=config.model,
            endpoint=endpoint,
            http_status_code=status_code,
            raw_response_preview=_build_response_preview(detail),
            response_text_source="none",
            attempt_context=attempt_context,
        )
        raise AIClientError(
            category=category,
            detail=f"AI request failed with HTTP {status_code}: {detail}",
        ) from exc
    except httpx.RequestError as exc:
        raise AIClientError(
            category="connection_error",
            detail=f"AI connection failed: {exc}",
        ) from exc
    except ValueError as exc:
        raise AIClientError(
            category="invalid_response_format",
            detail=f"AI response JSON decoding failed: {exc}",
        ) from exc

    raw_response_preview = _build_response_preview(
        response.text if hasattr(response, "text") else _safe_json_dumps(response_json)
    )
    try:
        text = _ollama_response_text(response_json)
    except ValueError as exc:
        _log_response_attempt(
            provider=config.provider,
            model=config.model,
            endpoint=endpoint,
            http_status_code=200,
            raw_response_preview=raw_response_preview,
            response_text_source="none",
            attempt_context=attempt_context,
        )
        raise AIClientError(
            category="invalid_response_format",
            detail=str(exc),
        ) from exc

    _log_response_attempt(
        provider=config.provider,
        model=config.model,
        endpoint=endpoint,
        http_status_code=200,
        raw_response_preview=raw_response_preview,
        response_text_source="message.content",
        attempt_context=attempt_context,
    )
    return AICompletionResponse(
        text=text,
        response_text_source="message.content",
    )


async def _request_codex2gpt_text(
    *,
    config: AIProviderConfig,
    instructions: str,
    serialized_payload: str,
    max_tokens: int,
    attempt_context: AIAttemptContext,
) -> AICompletionResponse:
    base_url = _resolve_codex2gpt_base_url(config)
    request_body = {
        "model": config.model,
        "stream": True,
        "client_id": DEFAULT_CODEX2GPT_CLIENT_ID,
        "business_key": DEFAULT_CODEX2GPT_BUSINESS_KEY,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": serialized_payload},
        ],
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    if (config.api_key or "").strip():
        headers["Authorization"] = f"Bearer {config.api_key.strip()}"
    endpoint = f"{base_url}/chat/completions"
    _log_request_attempt(
        provider=config.provider,
        model=config.model,
        endpoint=endpoint,
        stream=True,
        request_body=request_body,
        message_values=[instructions, serialized_payload],
        attempt_context=attempt_context,
    )

    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                endpoint,
                json=request_body,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise AIClientError(
            category="timeout",
            detail=f"AI request timed out after {config.timeout_seconds:g}s while waiting for upstream response",
        ) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        detail = exc.response.text.strip() or str(exc)
        category = _classify_http_error_category(
            provider=config.provider,
            status_code=status_code,
            detail=detail,
        )
        _log_response_attempt(
            provider=config.provider,
            model=config.model,
            endpoint=endpoint,
            http_status_code=status_code,
            raw_response_preview=_build_response_preview(detail),
            response_text_source="none",
            attempt_context=attempt_context,
        )
        raise AIClientError(
            category=category,
            detail=f"AI request failed with HTTP {status_code}: {detail}",
        ) from exc
    except httpx.RequestError as exc:
        raise AIClientError(
            category="connection_error",
            detail=f"AI connection failed: {exc}",
        ) from exc

    raw_response_text = response.text if hasattr(response, "text") else ""
    raw_response_preview = _build_response_preview(raw_response_text)
    try:
        text, response_text_source = _codex2gpt_stream_response_text_and_source(raw_response_text)
    except ValueError as exc:
        _log_response_attempt(
            provider=config.provider,
            model=config.model,
            endpoint=endpoint,
            http_status_code=200,
            raw_response_preview=raw_response_preview,
            response_text_source="none",
            attempt_context=attempt_context,
        )
        raise AIClientError(
            category="invalid_response_format",
            detail=str(exc),
        ) from exc

    _log_response_attempt(
        provider=config.provider,
        model=config.model,
        endpoint=endpoint,
        http_status_code=200,
        raw_response_preview=raw_response_preview,
        response_text_source=response_text_source,
        attempt_context=attempt_context,
    )
    return AICompletionResponse(
        text=text,
        response_text_source=response_text_source,
    )


def _serialize_payload(payload: object) -> str:
    if is_dataclass(payload):
        payload = asdict(payload)
    return json.dumps(payload, ensure_ascii=False)


def _resolve_total_attempts(retry_count_override: int | None) -> int:
    if retry_count_override is None:
        retry_count = MAX_AI_REQUEST_RETRIES
    else:
        retry_count = max(0, int(retry_count_override))
    return 1 + retry_count


def _config_with_timeout(config: AIProviderConfig, timeout_seconds: float) -> AIProviderConfig:
    return AIProviderConfig(
        provider=config.provider,
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        timeout_seconds=timeout_seconds,
    )


def _resolve_attempt_timeout_seconds(
    *,
    config_timeout_seconds: float,
    deadline: float | None,
) -> float:
    if deadline is None:
        return float(config_timeout_seconds)
    remaining_seconds = max(0.0, deadline - perf_counter())
    if remaining_seconds <= 0:
        raise AIClientError(
            category="timeout",
            detail="AI request timed out before the next attempt could start",
        )
    return max(0.1, min(float(config_timeout_seconds), remaining_seconds))


def _can_retry_within_budget(*, deadline: float | None, backoff_seconds: float) -> bool:
    if deadline is None:
        return True
    remaining_seconds = deadline - perf_counter()
    return remaining_seconds - backoff_seconds >= MIN_RETRY_BUDGET_SECONDS


def _is_retryable_ai_error(exc: AIClientError) -> bool:
    category = (exc.category or "").strip().lower()
    if category in RETRYABLE_HTTP_STATUS_CATEGORIES or category == "timeout":
        return True
    if category == "http_502_upstream_disconnect":
        return True
    if category != "connection_error":
        return False
    detail = (exc.detail or "").strip().lower()
    return any(marker in detail for marker in RETRYABLE_CONNECTION_ERROR_MARKERS)


def _classify_http_error_category(*, provider: str, status_code: int, detail: str) -> str:
    if status_code == 401:
        return "auth_error"
    if status_code == 403:
        return "permission_error"

    normalized_provider = (provider or "").strip().lower()
    normalized_detail = (detail or "").strip().lower()
    if normalized_provider == "codex2gpt" and status_code == 502:
        if any(marker in normalized_detail for marker in UPSTREAM_DISCONNECT_ERROR_MARKERS):
            return "http_502_upstream_disconnect"

    return f"http_{status_code}"


def _log_request_attempt(
    *,
    provider: str,
    model: str,
    endpoint: str,
    stream: bool,
    request_body: object,
    message_values: list[str],
    attempt_context: AIAttemptContext,
) -> None:
    logger.info(
        "AI request attempt provider=%s model=%s endpoint=%s stream=%s timeout=%s retry_count=%s attempt_index=%s attempt_total=%s request_body_bytes=%s messages_count=%s each_message_length=%s total_prompt_chars=%s",
        provider,
        model,
        endpoint,
        stream,
        round(attempt_context.timeout_seconds, 3),
        attempt_context.retry_count,
        attempt_context.attempt_index,
        attempt_context.attempt_total,
        len(_safe_json_dumps(request_body).encode("utf-8")),
        len(message_values),
        [len(value) for value in message_values],
        sum(len(value) for value in message_values),
    )


def _log_response_attempt(
    *,
    provider: str,
    model: str,
    endpoint: str,
    http_status_code: int | None,
    raw_response_preview: str,
    response_text_source: str,
    attempt_context: AIAttemptContext,
) -> None:
    logger.info(
        "AI response received provider=%s model=%s endpoint=%s attempt_index=%s attempt_total=%s http_status_code=%s raw_response_preview=%s response_text_source=%s",
        provider,
        model,
        endpoint,
        attempt_context.attempt_index,
        attempt_context.attempt_total,
        http_status_code,
        raw_response_preview,
        response_text_source,
    )


def _log_attempt_exception(
    *,
    provider: str,
    model: str,
    attempt_context: AIAttemptContext,
    exc: AIClientError,
) -> None:
    logger.warning(
        "AI request failed provider=%s model=%s attempt_index=%s attempt_total=%s exception_class=%s exception_message=%s error_category=%s",
        provider,
        model,
        attempt_context.attempt_index,
        attempt_context.attempt_total,
        exc.__class__.__name__,
        exc.detail,
        exc.category,
    )


def _safe_json_dumps(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        return str(value)


def _build_response_preview(value: str | object) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = _safe_json_dumps(value)
    normalized = " ".join(text.split())
    if len(normalized) <= RAW_RESPONSE_PREVIEW_LIMIT:
        return normalized
    return normalized[:RAW_RESPONSE_PREVIEW_LIMIT]


def _anthropic_response_payload(response: object) -> dict[str, object]:
    content_items = []
    for block in getattr(response, "content", []) or []:
        content_items.append(
            {
                "type": getattr(block, "type", None),
                "text": getattr(block, "text", None),
            }
        )
    return {
        "id": getattr(response, "id", None),
        "type": getattr(response, "type", None),
        "role": getattr(response, "role", None),
        "stop_reason": getattr(response, "stop_reason", None),
        "content": content_items,
    }


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
    content_types: list[str] = []
    for block in content:
        block_type = getattr(block, "type", None)
        if isinstance(block_type, str) and block_type:
            content_types.append(block_type)
        if block_type == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str):
                chunks.append(text)

    if not chunks:
        stop_reason = getattr(response, "stop_reason", None)
        raise ValueError(
            "AI response did not contain assistant text "
            f"(stop_reason={stop_reason}, content_types={content_types})"
        )

    logger.info(
        "AI Anthropic text extracted content_items=%s text_chunks=%s text_chars=%s",
        len(content),
        len(chunks),
        len("".join(chunks)),
    )

    return "".join(chunks)


def _ollama_response_text(response: object) -> str:
    if not isinstance(response, dict):
        raise ValueError("AI response root must be an object")

    message = response.get("message")
    if not isinstance(message, dict):
        raise ValueError("AI response did not contain a message object")

    text = message.get("content")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "AI response did not contain assistant text "
            f"(done_reason={response.get('done_reason')})"
        )

    logger.info(
        "AI Ollama text extracted text_chars=%s",
        len(text),
    )
    return text


def _resolve_base_url(config: AIProviderConfig) -> str:
    configured = (config.base_url or "").strip()
    if configured:
        return configured
    env_base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()
    if env_base_url:
        return env_base_url
    return DEFAULT_MINIMAX_ANTHROPIC_BASE_URL


def _resolve_ollama_base_url(config: AIProviderConfig) -> str:
    configured = (config.base_url or "").strip()
    resolved = configured or DEFAULT_OLLAMA_BASE_URL
    rewritten = _rewrite_local_url_for_container(resolved)
    if rewritten != resolved.rstrip("/"):
        logger.info(
            "AI Ollama base URL rewritten for container access from=%s to=%s",
            resolved.rstrip("/"),
            rewritten,
        )
    return rewritten


def _resolve_codex2gpt_base_url(config: AIProviderConfig) -> str:
    configured = (config.base_url or "").strip()
    resolved = configured or DEFAULT_CODEX2GPT_BASE_URL
    rewritten = _rewrite_local_url_for_container(resolved)
    if rewritten != resolved.rstrip("/"):
        logger.info(
            "AI codex2gpt base URL rewritten for container access from=%s to=%s",
            resolved.rstrip("/"),
            rewritten,
        )
    return rewritten


def _rewrite_local_url_for_container(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if not _is_running_in_docker():
        return normalized

    parsed = urlsplit(normalized)
    hostname = parsed.hostname or ""
    if hostname not in {"127.0.0.1", "localhost"}:
        return normalized

    host = "host.docker.internal"
    netloc = host
    if parsed.port is not None:
        netloc = f"{host}:{parsed.port}"
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        netloc = f"{auth}@{netloc}"

    return urlunsplit(
        SplitResult(
            scheme=parsed.scheme,
            netloc=netloc,
            path=parsed.path,
            query=parsed.query,
            fragment=parsed.fragment,
        )
    ).rstrip("/")


def _is_running_in_docker() -> bool:
    return os.path.exists("/.dockerenv")


def _codex2gpt_response_text(response: object) -> str:
    text, _ = _codex2gpt_response_text_and_source(response)
    return text


def _codex2gpt_stream_response_text_and_source(raw_response_text: str) -> tuple[str, str]:
    event_payloads: list[dict[str, object]] = []
    delta_chunks: list[str] = []

    for raw_line in raw_response_text.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("data: "):
            continue

        payload_text = line[6:].strip()
        if payload_text == "[DONE]":
            continue

        try:
            payload = json.loads(payload_text)
        except JSONDecodeError as exc:
            raise ValueError(f"AI response stream contained invalid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            continue

        event_payloads.append(payload)
        first_choice = payload.get("choices")
        choice = first_choice[0] if isinstance(first_choice, list) and first_choice and isinstance(first_choice[0], dict) else None
        if choice is None:
            continue

        delta = choice.get("delta")
        if not isinstance(delta, dict):
            continue

        content = delta.get("content")
        if isinstance(content, str) and content:
            delta_chunks.append(content)
            continue

        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    delta_chunks.append(item["text"])

    normalized_delta = "".join(delta_chunks).strip()
    if normalized_delta:
        logger.info(
            "AI codex2gpt text extracted source=%s chunk_count=%s text_chars=%s",
            "choices[0].delta.content",
            len(delta_chunks),
            len(normalized_delta),
        )
        return normalized_delta, "choices[0].delta.content"

    for payload in event_payloads:
        try:
            text, source = _codex2gpt_response_text_and_source(payload)
        except ValueError:
            continue
        normalized_text = text.strip()
        if normalized_text:
            return normalized_text, f"stream.{source}"

    stripped_response = raw_response_text.strip()
    if stripped_response.startswith("{"):
        try:
            payload = json.loads(stripped_response)
        except JSONDecodeError as exc:
            raise ValueError(f"AI response JSON decoding failed: {exc.msg}") from exc
        return _codex2gpt_response_text_and_source(payload)

    raise ValueError("AI response stream did not contain assistant text")


def _codex2gpt_response_text_and_source(response: object) -> tuple[str, str]:
    if not isinstance(response, dict):
        raise ValueError("AI response root must be an object")

    choices = response.get("choices")
    first_choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
    if first_choice is not None:
        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                logger.info(
                    "AI codex2gpt text extracted source=%s text_chars=%s",
                    "choices[0].message.content",
                    len(content),
                )
                return content, "choices[0].message.content"
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                normalized = "".join(parts).strip()
                if normalized:
                    logger.info(
                        "AI codex2gpt text extracted source=%s content_parts=%s text_chars=%s",
                        "choices[0].message.content",
                        len(parts),
                        len(normalized),
                    )
                    return normalized, "choices[0].message.content"

        text = first_choice.get("text")
        if isinstance(text, str) and text.strip():
            logger.info(
                "AI codex2gpt text extracted source=%s text_chars=%s",
                "choices[0].text",
                len(text),
            )
            return text, "choices[0].text"

    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        logger.info(
            "AI codex2gpt text extracted source=%s text_chars=%s",
            "output_text",
            len(output_text),
        )
        return output_text, "output_text"

    nested_response = response.get("response")
    if isinstance(nested_response, dict):
        nested_output_text = nested_response.get("output_text")
        if isinstance(nested_output_text, str) and nested_output_text.strip():
            logger.info(
                "AI codex2gpt text extracted source=%s text_chars=%s",
                "response.output_text",
                len(nested_output_text),
            )
            return nested_output_text, "response.output_text"

    if not isinstance(choices, list) or not choices:
        raise ValueError("AI response did not contain choices")
    raise ValueError("AI response did not contain assistant text")


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
