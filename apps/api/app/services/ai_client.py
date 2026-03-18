import json
from __future__ import annotations
from dataclasses import asdict, dataclass, is_dataclass
import httpx

EMPTY_PROVIDER_VALUES = {"", "disabled", "none", "off"}
ANTHROPIC_COMPATIBLE_PROVIDERS = {"minimax", "anthropic"}


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
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    headers.update(_anthropic_auth_headers(config))

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
    response.raise_for_status()


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
