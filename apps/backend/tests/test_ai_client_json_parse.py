from __future__ import annotations

import os

import pytest

from app.services.ai_client import (
    AIClientError,
    AIProviderConfig,
    _build_anthropic_client_kwargs,
    request_json_completion,
)


@pytest.mark.asyncio
async def test_request_json_completion_accepts_first_json_when_extra_data_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_anthropic_text(**_: object) -> str:
        return (
            '{"structured_json":{"basic_info":{"name":"Alice"}}}\n'
            '{"debug":"extra block"}'
        )

    monkeypatch.setattr(
        "app.services.ai_client._request_anthropic_text",
        fake_request_anthropic_text,
    )

    payload = await request_json_completion(
        config=AIProviderConfig(
            provider="minimax",
            base_url="https://api.minimaxi.com/anthropic",
            api_key="test-key",
            model="MiniMax-M2.5",
            timeout_seconds=30,
        ),
        instructions="Return strict JSON",
        payload={"raw_text": "hello"},
    )

    assert payload == {"structured_json": {"basic_info": {"name": "Alice"}}}


@pytest.mark.asyncio
async def test_request_json_completion_parses_json_inside_code_fence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request_anthropic_text(**_: object) -> str:
        return (
            "```json\n"
            '{"structured_json":{"basic_info":{"name":"Bob"}}}\n'
            "```"
        )

    monkeypatch.setattr(
        "app.services.ai_client._request_anthropic_text",
        fake_request_anthropic_text,
    )

    payload = await request_json_completion(
        config=AIProviderConfig(
            provider="minimax",
            base_url="https://api.minimaxi.com/anthropic",
            api_key="test-key",
            model="MiniMax-M2.5",
            timeout_seconds=30,
        ),
        instructions="Return strict JSON",
        payload={"raw_text": "hello"},
    )

    assert payload == {"structured_json": {"basic_info": {"name": "Bob"}}}


@pytest.mark.asyncio
async def test_request_json_completion_retries_once_on_timeout_and_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    async def fake_request_anthropic_text(**_: object) -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise AIClientError(category="timeout", detail="timeout")
        return '{"structured_json":{"basic_info":{"name":"RetryOK"}}}'

    monkeypatch.setattr(
        "app.services.ai_client._request_anthropic_text",
        fake_request_anthropic_text,
    )

    payload = await request_json_completion(
        config=AIProviderConfig(
            provider="minimax",
            base_url="https://api.minimaxi.com/anthropic",
            api_key="test-key",
            model="MiniMax-M2.5",
            timeout_seconds=30,
        ),
        instructions="Return strict JSON",
        payload={"raw_text": "hello"},
    )

    assert attempts["count"] == 2
    assert payload == {"structured_json": {"basic_info": {"name": "RetryOK"}}}


@pytest.mark.asyncio
async def test_request_json_completion_raises_after_retry_exhausted_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    async def fake_request_anthropic_text(**_: object) -> str:
        attempts["count"] += 1
        raise AIClientError(category="timeout", detail="timeout")

    monkeypatch.setattr(
        "app.services.ai_client._request_anthropic_text",
        fake_request_anthropic_text,
    )

    with pytest.raises(AIClientError) as exc_info:
        await request_json_completion(
            config=AIProviderConfig(
                provider="minimax",
                base_url="https://api.minimaxi.com/anthropic",
                api_key="test-key",
                model="MiniMax-M2.5",
                timeout_seconds=30,
            ),
            instructions="Return strict JSON",
            payload={"raw_text": "hello"},
        )

    assert attempts["count"] == 2
    assert exc_info.value.category == "timeout"


def test_build_anthropic_client_kwargs_uses_auth_token_for_minimax() -> None:
    kwargs = _build_anthropic_client_kwargs(
        AIProviderConfig(
            provider="minimax",
            base_url="https://api.minimaxi.com/anthropic",
            api_key="test-key",
            model="MiniMax-M2.5",
            timeout_seconds=30,
        )
    )

    assert kwargs["base_url"] == "https://api.minimaxi.com/anthropic"
    assert kwargs["auth_token"] == "test-key"
    assert "api_key" not in kwargs


def test_build_anthropic_client_kwargs_uses_env_base_url_when_config_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic")

    kwargs = _build_anthropic_client_kwargs(
        AIProviderConfig(
            provider="minimax",
            base_url="",
            api_key="test-key",
            model="MiniMax-M2.5",
            timeout_seconds=30,
        )
    )

    assert kwargs["base_url"] == os.environ["ANTHROPIC_BASE_URL"]
