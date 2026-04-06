from __future__ import annotations

import httpx
import pytest

from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion, request_text_completion


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://127.0.0.1:11434/api/chat")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("request failed", request=request, response=response)

    def json(self) -> dict[str, object]:
        return self._payload


@pytest.mark.asyncio
async def test_request_text_completion_uses_codex2gpt_chat_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def post(
            self,
            url: str,
            *,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> _FakeResponse:
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "OK from codex2gpt",
                            }
                        }
                    ]
                }
            )

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="codex2gpt",
            base_url="http://127.0.0.1:18100/v1",
            api_key=None,
            model="gpt-5.4",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK from codex2gpt.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK from codex2gpt"
    assert captured["timeout"] == 20
    assert captured["url"] == "http://127.0.0.1:18100/v1/chat/completions"
    assert captured["headers"] == {"Content-Type": "application/json"}
    assert captured["json"] == {
        "model": "gpt-5.4",
        "stream": False,
        "client_id": "career-pilot-backend",
        "business_key": "career-pilot",
        "messages": [
            {"role": "system", "content": "Reply with exactly OK from codex2gpt."},
            {"role": "user", "content": '{"ping": "pong"}'},
        ],
        "max_tokens": 20,
    }


@pytest.mark.asyncio
async def test_request_text_completion_rewrites_local_codex2gpt_url_inside_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def post(
            self,
            url: str,
            *,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> _FakeResponse:
            del json, headers
            captured["url"] = url
            return _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "OK",
                            }
                        }
                    ]
                }
            )

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("app.services.ai_client._is_running_in_docker", lambda: True)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="codex2gpt",
            base_url="http://127.0.0.1:18100/v1",
            api_key=None,
            model="gpt-5.4",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK"
    assert captured["url"] == "http://host.docker.internal:18100/v1/chat/completions"


@pytest.mark.asyncio
async def test_request_text_completion_uses_ollama_chat_api(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def post(self, url: str, *, json: dict[str, object]) -> _FakeResponse:
            captured["url"] = url
            captured["json"] = json
            return _FakeResponse(
                {
                    "message": {"role": "assistant", "content": "OK"},
                    "done": True,
                    "done_reason": "stop",
                }
            )

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            api_key=None,
            model="qwen2.5:7b",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK"
    assert captured["timeout"] == 20
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["json"] == {
        "model": "qwen2.5:7b",
        "stream": False,
        "keep_alive": "10m",
        "messages": [
            {"role": "system", "content": "Reply with exactly OK."},
            {"role": "user", "content": '{"ping": "pong"}'},
        ],
        "options": {"num_predict": 20},
    }


@pytest.mark.asyncio
async def test_request_text_completion_rewrites_local_ollama_url_inside_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def post(self, url: str, *, json: dict[str, object]) -> _FakeResponse:
            captured["url"] = url
            captured["json"] = json
            return _FakeResponse(
                {
                    "message": {"role": "assistant", "content": "OK"},
                    "done": True,
                    "done_reason": "stop",
                }
            )

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("app.services.ai_client._is_running_in_docker", lambda: True)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            api_key=None,
            model="qwen2.5:7b",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK"
    assert captured["url"] == "http://host.docker.internal:11434/api/chat"


@pytest.mark.asyncio
async def test_request_json_completion_extracts_json_from_ollama_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            del timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def post(self, url: str, *, json: dict[str, object]) -> _FakeResponse:
            del url, json
            return _FakeResponse(
                {
                    "message": {
                        "role": "assistant",
                        "content": '```json\n{"status":"ok","score":88}\n```',
                    },
                    "done": True,
                    "done_reason": "stop",
                }
            )

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    payload = await request_json_completion(
        config=AIProviderConfig(
            provider="ollama",
            base_url="http://127.0.0.1:11434",
            api_key=None,
            model="qwen2.5:7b",
            timeout_seconds=20,
        ),
        instructions="Return a JSON object.",
        payload={"ping": "pong"},
        max_tokens=64,
    )

    assert payload == {"status": "ok", "score": 88}


@pytest.mark.asyncio
async def test_request_text_completion_maps_ollama_timeout_to_ai_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            del timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def post(self, url: str, *, json: dict[str, object]) -> _FakeResponse:
            del url, json
            raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(AIClientError) as exc_info:
        await request_text_completion(
            config=AIProviderConfig(
                provider="ollama",
                base_url="http://127.0.0.1:11434",
                api_key=None,
                model="qwen2.5:7b",
                timeout_seconds=20,
            ),
            instructions="Reply with exactly OK.",
            payload={"ping": "pong"},
            max_tokens=20,
        )

    assert exc_info.value.category == "timeout"


@pytest.mark.asyncio
async def test_request_text_completion_respects_retry_count_override_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            del timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        async def post(self, url: str, *, json: dict[str, object]) -> _FakeResponse:
            del url, json
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(AIClientError) as exc_info:
        await request_text_completion(
            config=AIProviderConfig(
                provider="ollama",
                base_url="http://127.0.0.1:11434",
                api_key=None,
                model="qwen2.5:7b",
                timeout_seconds=20,
            ),
            instructions="Reply with exactly OK.",
            payload={"ping": "pong"},
            max_tokens=20,
            retry_count_override=0,
        )

    assert exc_info.value.category == "timeout"
    assert calls == 1
