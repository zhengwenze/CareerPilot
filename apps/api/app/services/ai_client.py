from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, is_dataclass

import httpx

EMPTY_PROVIDER_VALUES = {"", "disabled", "none", "off"}
ANTHROPIC_COMPATIBLE_PROVIDERS = {"minimax", "anthropic"}
MAX_ERROR_BODY_LENGTH = 240
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AIProviderConfig:
    provider: str
    base_url: str
    api_key: str | None
    model: str
    timeout_seconds: int


async def request_json_completion(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
    max_tokens: int = 4000,
) -> dict[str, object]:
    if config.provider in ANTHROPIC_COMPATIBLE_PROVIDERS:
        content = await _request_anthropic_text(
            config=config,
            instructions=instructions,
            payload=payload,
            max_tokens=max_tokens,
        )
    else:
        content = await _request_openai_text(
            config=config,
            instructions=instructions,
            payload=payload,
        )
    return json.loads(_extract_json_object(content))


async def _request_openai_text(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
) -> str:
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
        response = await client.post(
            f"{config.base_url.rstrip('/')}/responses",
            headers=headers,
            json={
                "model": config.model,
                "stream": False,
                "instructions": instructions,
                "input": _serialize_payload(payload),
                "reasoning": {"effort": "low"},
                "text": {"verbosity": "low"},
            },
        )
        _raise_for_status_with_context(
            response,
            provider=config.provider,
            model=config.model,
        )

    return _openai_response_text(response.json())


async def _request_anthropic_text(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
    max_tokens: int,
) -> str:
    logger.debug(
        (
            "AI provider request starting: provider=%s model=%s "
            "instructions_length=%d payload_type=%s max_tokens=%d"
        ),
        config.provider,
        config.model,
        len(instructions),
        type(payload).__name__,
        max_tokens,
    )

    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    headers.update(_anthropic_auth_headers(config))

    logger.debug(
        "AI provider request headers: provider=%s has_api_key=%s",
        config.provider,
        bool(config.api_key),
    )

    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
        response = await client.post(
            _anthropic_messages_endpoint(config.base_url),
            headers=headers,
            json={
                "model": config.model,
                "max_tokens": max_tokens,
                "system": instructions,
                "messages": [
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
            },
        )

        logger.debug(
            (
                "AI provider request completed: provider=%s model=%s "
                "status=%d url=%s"
            ),
            config.provider,
            config.model,
            response.status_code,
            str(response.request.url),
        )

        _raise_for_status_with_context(
            response,
            provider=config.provider,
            model=config.model,
        )

    return _anthropic_response_text(response.json())


def _serialize_payload(payload: object) -> str:
    if is_dataclass(payload):
        payload = asdict(payload)
    return json.dumps(payload, ensure_ascii=False)


def _anthropic_auth_headers(config: AIProviderConfig) -> dict[str, str]:
    if not config.api_key:
        return {}
    if config.provider == "minimax":
        return {"Authorization": f"Bearer {config.api_key}"}
    return {"x-api-key": config.api_key}


def _raise_for_status_with_context(
    response: httpx.Response,
    *,
    provider: str,
    model: str,
) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body_excerpt = _response_body_excerpt(response)
        full_body = response.text.strip() if response.text else "<empty>"
        logger.warning(
            (
                "AI provider request failed: provider=%s model=%s status=%s url=%s "
                "request_id=%s response_full=%s"
            ),
            provider,
            model,
            response.status_code,
            str(response.request.url),
            response.headers.get("x-request-id", "unknown"),
            full_body,
        )
        raise RuntimeError(
            (
                "AI provider request failed: provider=%s model=%s status=%s url=%s "
                "response_excerpt=%s"
            )
            % (
                provider,
                model,
                response.status_code,
                str(response.request.url),
                body_excerpt,
            )
        ) from exc


def _response_body_excerpt(response: httpx.Response) -> str:
    body = response.text.strip()
    if not body:
        return "<empty>"
    normalized = " ".join(body.split())
    if len(normalized) <= MAX_ERROR_BODY_LENGTH:
        return normalized
    return f"{normalized[:MAX_ERROR_BODY_LENGTH]}..."


def _extract_json_object(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("AI response did not contain a JSON object")
    return content[start : end + 1]


def _anthropic_messages_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1/messages"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/messages"
    return f"{normalized}/v1/messages"


def _anthropic_response_text(response: dict[str, object]) -> str:
    content = response.get("content")
    if not isinstance(content, list):
        raise ValueError("AI response did not contain content items")

    chunks: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            chunks.append(part["text"])

    if not chunks:
        raise ValueError("AI response did not contain assistant text")
    return "".join(chunks)


def _openai_response_text(response: dict[str, object]) -> str:
    output = response.get("output")
    if not isinstance(output, list):
        raise ValueError("AI response did not contain output items")

    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                chunks.append(part["text"])

    if not chunks:
        raise ValueError("AI response did not contain assistant text")
    return "".join(chunks)
