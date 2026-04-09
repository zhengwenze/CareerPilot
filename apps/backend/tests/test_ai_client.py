from __future__ import annotations

import json
import logging

import httpx
import pytest

from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion, request_text_completion


class _FakeResponse:
    def __init__(
        self,
        payload: dict[str, object],
        status_code: int = 200,
        *,
        text: str | None = None,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text if text is not None else str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://127.0.0.1:11434/api/chat")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("request failed", request=request, response=response)

    def json(self) -> dict[str, object]:
        return self._payload


def _sse_payload_text(*payloads: dict[str, object]) -> str:
    lines = [f"data: {json_payload}" for json_payload in (json.dumps(payload, ensure_ascii=False) for payload in payloads)]
    lines.append("data: [DONE]")
    return "\n".join(lines)


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
                {},
                text=_sse_payload_text(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "role": "assistant",
                                    "content": "OK from codex2gpt",
                                }
                            }
                        ]
                    }
                ),
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
        "stream": True,
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
            return _FakeResponse({}, text=_sse_payload_text({"choices": [{"delta": {"content": "OK"}}]}))

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


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [502, 503, 504])
async def test_request_text_completion_retries_retryable_http_statuses(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    calls = 0

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            nonlocal calls
            calls += 1
            if calls == 1:
                return _FakeResponse({"error": "upstream failure"}, status_code=status_code)
            return _FakeResponse({}, text=_sse_payload_text({"choices": [{"delta": {"content": "OK after retry"}}]}))

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="codex2gpt",
            base_url="http://127.0.0.1:18100/v1",
            api_key=None,
            model="gpt-5.4",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK after retry.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK after retry"
    assert calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_category"),
    [(401, "auth_error"), (403, "permission_error"), (422, "http_422")],
)
async def test_request_text_completion_does_not_retry_nonretryable_http_statuses(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_category: str,
) -> None:
    calls = 0

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            nonlocal calls
            calls += 1
            return _FakeResponse({"error": "not retryable"}, status_code=status_code)

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(AIClientError) as exc_info:
        await request_text_completion(
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

    assert exc_info.value.category == expected_category
    assert calls == 1


@pytest.mark.asyncio
async def test_request_text_completion_retries_retryable_connection_error_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            nonlocal calls
            calls += 1
            if calls == 1:
                raise httpx.RemoteProtocolError("Remote end closed connection without response")
            return _FakeResponse({}, text=_sse_payload_text({"choices": [{"delta": {"content": "OK after reconnect"}}]}))

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="codex2gpt",
            base_url="http://127.0.0.1:18100/v1",
            api_key=None,
            model="gpt-5.4",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK after reconnect.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK after reconnect"
    assert calls == 2


@pytest.mark.asyncio
async def test_request_text_completion_extracts_text_from_choices_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            return _FakeResponse({}, text=_sse_payload_text({"choices": [{"text": "OK via choices text"}]}))

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="codex2gpt",
            base_url="http://127.0.0.1:18100/v1",
            api_key=None,
            model="gpt-5.4",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK via choices text.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK via choices text"


@pytest.mark.asyncio
async def test_request_text_completion_extracts_text_from_output_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            return _FakeResponse({}, text=_sse_payload_text({"choices": [], "output_text": "OK via output_text"}))

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="codex2gpt",
            base_url="http://127.0.0.1:18100/v1",
            api_key=None,
            model="gpt-5.4",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK via output_text.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK via output_text"


@pytest.mark.asyncio
async def test_request_text_completion_extracts_text_from_nested_response_output_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            return _FakeResponse(
                {},
                text=_sse_payload_text({"choices": [], "response": {"output_text": "OK via nested output_text"}}),
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
        instructions="Reply with exactly OK via nested output_text.",
        payload={"ping": "pong"},
        max_tokens=20,
    )

    assert text == "OK via nested output_text"


@pytest.mark.asyncio
async def test_request_text_completion_returns_invalid_response_format_when_no_text_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            nonlocal calls
            calls += 1
            return _FakeResponse({}, text=_sse_payload_text({"choices": [{"message": {"role": "assistant", "content": None}}]}))

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(AIClientError) as exc_info:
        await request_text_completion(
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

    assert exc_info.value.category == "invalid_response_format"
    assert calls == 1


@pytest.mark.asyncio
async def test_request_text_completion_skips_retry_when_budget_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    sleep_calls = 0
    perf_values = iter([100.0, 100.0, 117.3])

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            nonlocal calls
            calls += 1
            return _FakeResponse({"error": "upstream closed"}, status_code=502)

    async def fake_sleep(seconds: float) -> None:
        del seconds
        nonlocal sleep_calls
        sleep_calls += 1

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("app.services.ai_client.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("app.services.ai_client.perf_counter", lambda: next(perf_values))

    with pytest.raises(AIClientError) as exc_info:
        await request_text_completion(
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
            retry_count_override=1,
            total_timeout_budget_seconds=20,
        )

    assert exc_info.value.category == "http_502"
    assert calls == 1
    assert sleep_calls == 0


@pytest.mark.asyncio
async def test_request_text_completion_logs_diagnostics_without_payload_leak(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_resume_text = "SECRET_RESUME_LINE_SHOULD_NOT_APPEAR_IN_LOGS"

    class FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            del timeout

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
            del url, json, headers
            return _FakeResponse({}, text=_sse_payload_text({"choices": [{"delta": {"content": "OK"}}]}))

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", FakeAsyncClient)
    caplog.set_level(logging.INFO)

    text = await request_text_completion(
        config=AIProviderConfig(
            provider="codex2gpt",
            base_url="http://127.0.0.1:18100/v1",
            api_key=None,
            model="gpt-5.4",
            timeout_seconds=20,
        ),
        instructions="Reply with exactly OK.",
        payload={"resume": secret_resume_text},
        max_tokens=20,
    )

    assert text == "OK"
    assert "endpoint=http://127.0.0.1:18100/v1/chat/completions" in caplog.text
    assert "request_body_bytes=" in caplog.text
    assert "messages_count=2" in caplog.text
    assert "each_message_length=" in caplog.text
    assert "total_prompt_chars=" in caplog.text
    assert "http_status_code=200" in caplog.text
    assert "raw_response_preview=" in caplog.text
    assert "response_text_source=choices[0].delta.content" in caplog.text
    assert "exception_class=" not in caplog.text
    assert secret_resume_text not in caplog.text
