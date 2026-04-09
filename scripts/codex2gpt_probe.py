#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from time import perf_counter

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "apps" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings
from app.prompts.resume import get_resume_pdf_to_md_prompt
from app.services.ai_client import (  # noqa: E402
    AIProviderConfig,
    DEFAULT_CODEX2GPT_BUSINESS_KEY,
    DEFAULT_CODEX2GPT_CLIENT_ID,
    _build_response_preview,
    _codex2gpt_response_text_and_source,
    _resolve_codex2gpt_base_url,
)
from app.services.resume import build_resume_pdf_ai_configs, load_resume_pdf_to_md_module  # noqa: E402


REAL_SAMPLE_MARKDOWN = """# 张三

- 邮箱：zhangsan@example.com
- 电话：13800138000
- GitHub：https://github.com/example
- LinkedIn：https://www.linkedin.com/in/example

## 教育经历
- 示例大学 软件工程 本科 | 2020.09 - 2024.06

## 工作经历
### 示例科技 | 后端开发实习生 | 2023.06 - 2023.12
- 负责 FastAPI 服务开发与接口联调
- 参与简历解析与结构化数据链路优化

## 项目经历
### Career Pilot
- 设计并实现 PDF 简历转 Markdown 的数据清洗流程
- 优化日志与错误分类，提升排障效率

## 技能
- Python, FastAPI, PostgreSQL, Redis, Docker
"""


def _build_codex2gpt_request(
    *,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
) -> tuple[str, dict[str, str], dict[str, object], list[str]]:
    serialized_payload = json.dumps(payload, ensure_ascii=False)
    endpoint = f"{_resolve_codex2gpt_base_url(config)}/chat/completions"
    request_body = {
        "model": config.model,
        "stream": False,
        "client_id": DEFAULT_CODEX2GPT_CLIENT_ID,
        "business_key": DEFAULT_CODEX2GPT_BUSINESS_KEY,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": serialized_payload},
        ],
        "max_tokens": 4000,
    }
    headers = {"Content-Type": "application/json"}
    if (config.api_key or "").strip():
        headers["Authorization"] = f"Bearer {config.api_key.strip()}"
    return endpoint, headers, request_body, [instructions, serialized_payload]


async def _run_case(
    *,
    name: str,
    config: AIProviderConfig,
    instructions: str,
    payload: object,
) -> dict[str, object]:
    endpoint, headers, request_body, message_values = _build_codex2gpt_request(
        config=config,
        instructions=instructions,
        payload=payload,
    )
    started = perf_counter()
    result = {
        "case": name,
        "status": "error",
        "category": "",
        "latency_ms": None,
        "request_body_bytes": len(json.dumps(request_body, ensure_ascii=False).encode("utf-8")),
        "messages_count": len(message_values),
        "each_message_length": [len(value) for value in message_values],
        "response_text_source": "none",
        "response_preview": "",
    }

    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(endpoint, json=request_body, headers=headers)
            result["latency_ms"] = max(0, int((perf_counter() - started) * 1000))
            response.raise_for_status()
            response_json = response.json()
            try:
                text, response_text_source = _codex2gpt_response_text_and_source(response_json)
            except ValueError:
                result["category"] = "invalid_response_format"
                result["response_preview"] = _build_response_preview(response.text)
                return result

            result["status"] = "success"
            result["category"] = "success"
            result["response_text_source"] = response_text_source
            result["response_preview"] = _build_response_preview(response.text or text)
            return result
    except httpx.HTTPStatusError as exc:
        result["latency_ms"] = max(0, int((perf_counter() - started) * 1000))
        result["category"] = f"http_{exc.response.status_code}"
        result["response_preview"] = _build_response_preview(exc.response.text)
        return result
    except httpx.TimeoutException as exc:
        result["latency_ms"] = max(0, int((perf_counter() - started) * 1000))
        result["category"] = "timeout"
        result["response_preview"] = _build_response_preview(str(exc))
        return result
    except httpx.RequestError as exc:
        result["latency_ms"] = max(0, int((perf_counter() - started) * 1000))
        result["category"] = "connection_error"
        result["response_preview"] = _build_response_preview(str(exc))
        return result
    except ValueError as exc:
        result["latency_ms"] = max(0, int((perf_counter() - started) * 1000))
        result["category"] = "invalid_response_format"
        result["response_preview"] = _build_response_preview(str(exc))
        return result


def _build_probe_cases() -> list[tuple[str, str, object]]:
    module = load_resume_pdf_to_md_module()
    build_pdf_to_md_user_prompt = getattr(module, "build_pdf_to_md_user_prompt")

    medium_text = (
        "Career Pilot probe medium payload. "
        "This sentence exists to verify whether request size materially changes gateway behavior. "
    ) * 8

    real_payload = {
        "raw_markdown": REAL_SAMPLE_MARKDOWN,
        "user_prompt": build_pdf_to_md_user_prompt(REAL_SAMPLE_MARKDOWN),
    }
    return [
        ("small", "You are a diagnostic probe. Reply with exactly OK.", {"prompt": "Reply with OK only."}),
        ("medium", "Read the provided text and reply with exactly OK.", {"text": medium_text}),
        ("real", get_resume_pdf_to_md_prompt(), real_payload),
    ]


def _classify_results(results: list[dict[str, object]]) -> str:
    categories = [str(item["category"]) for item in results]
    if categories and all(category == "http_502" for category in categories):
        return "all_502"

    case_map = {str(item["case"]): item for item in results}
    small_ok = str(case_map.get("small", {}).get("status")) == "success"
    medium_failed = str(case_map.get("medium", {}).get("status")) != "success"
    real_failed = str(case_map.get("real", {}).get("status")) != "success"
    if small_ok and medium_failed and real_failed:
        return "payload_or_long_request"

    if any(category == "invalid_response_format" for category in categories):
        return "protocol_compatibility_issue"

    return "mixed_or_unknown"


async def main() -> None:
    settings = Settings()
    ai_configs = build_resume_pdf_ai_configs(settings)
    if not ai_configs:
        raise SystemExit("No primary AI config available for resume PDF to MD probe")

    config = ai_configs[0]
    results = []
    for name, instructions, payload in _build_probe_cases():
        result = await _run_case(
            name=name,
            config=config,
            instructions=instructions,
            payload=payload,
        )
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    summary = {
        "summary_category": _classify_results(results),
        "provider": config.provider,
        "model": config.model,
        "timeout_seconds": config.timeout_seconds,
        "cases": [result["case"] for result in results],
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
