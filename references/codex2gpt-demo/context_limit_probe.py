#!/usr/bin/env python3
"""Stream=true context and prompt-complexity probe for codex2gpt."""

from __future__ import annotations

import argparse
import csv
import json
import socket
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "apps" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import DEFAULT_CODEX2GPT_MODEL, Settings  # noqa: E402
from app.prompts.tailored_resume import get_tailored_resume_full_document_prompt  # noqa: E402
from app.schemas.resume import ResumeStructuredData  # noqa: E402
from app.schemas.tailored_resume import TailoredResumeDocument  # noqa: E402
from app.services.ai_client import (  # noqa: E402
    AIProviderConfig,
    DEFAULT_CODEX2GPT_BASE_URL,
    DEFAULT_CODEX2GPT_BUSINESS_KEY,
    DEFAULT_CODEX2GPT_CLIENT_ID,
    _build_response_preview,
    _extract_json_object,
    _resolve_local_base_url,
)
from app.services.resume_markdown_parser import parse_resume_markdown  # noqa: E402
from app.services.resume_markdown_renderer import render_resume_markdown  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_RESUME_FILE = FIXTURE_DIR / "resume_realistic.md"
DEFAULT_JD_FILE = FIXTURE_DIR / "jd_realistic.txt"
DEFAULT_FILLER_FILE = FIXTURE_DIR / "filler_neutral.txt"
DEFAULT_JSON_OUT = Path(__file__).resolve().parent / "context_limit_probe_result.real.json"
DEFAULT_CSV_OUT = Path(__file__).resolve().parent / "context_limit_probe_result.real.csv"
DEFAULT_REPORT_OUT = Path(__file__).resolve().parent / "context_limit_probe_report.md"
DEFAULT_SAMPLE_OUT = Path(__file__).resolve().parent / "context_limit_probe_result.sample.json"
DEFAULT_TARGET_SCALES = [2000, 4000, 8000, 12000, 16000, 24000, 32000, 48000, 64000]
DEFAULT_SAMPLE_SCALES = [2000, 4000]
DEFAULT_TIMEOUT = 120
DEFAULT_MAX_OUTPUT_TOKENS = 1800
SUCCESS_CLASSIFICATIONS = {"success_usable", "success_but_weak"}


@dataclass(frozen=True)
class BuiltRequest:
    instructions: str
    payload: dict[str, Any]
    estimated_input_tokens: int | None
    estimated_input_tokens_error: str | None
    input_chars: int
    payload_chars: int
    filler_repeat_count: int
    target_scale_tokens: int


def load_settings() -> Settings:
    return Settings()


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description="Probe codex2gpt stream=true behavior across prompt complexity groups."
    )
    parser.add_argument("--resume-file", default=str(DEFAULT_RESUME_FILE))
    parser.add_argument("--jd-file", default=str(DEFAULT_JD_FILE))
    parser.add_argument("--filler-file", default=str(DEFAULT_FILLER_FILE))
    parser.add_argument("--model", default=settings.resume_ai_model or DEFAULT_CODEX2GPT_MODEL)
    parser.add_argument("--base-url", default=settings.resume_ai_base_url or DEFAULT_CODEX2GPT_BASE_URL)
    parser.add_argument("--api-key", default=settings.resume_ai_api_key or "")
    parser.add_argument("--timeout", type=int, default=max(settings.resume_ai_timeout_seconds, DEFAULT_TIMEOUT))
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--count-tokens-model", default="")
    parser.add_argument("--target-scales", default=",".join(str(v) for v in DEFAULT_TARGET_SCALES))
    parser.add_argument("--sample-scales", default=",".join(str(v) for v in DEFAULT_SAMPLE_SCALES))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--csv-out", default=str(DEFAULT_CSV_OUT))
    parser.add_argument("--report-out", default=str(DEFAULT_REPORT_OUT))
    parser.add_argument("--client-id", default=DEFAULT_CODEX2GPT_CLIENT_ID)
    parser.add_argument("--business-key", default=DEFAULT_CODEX2GPT_BUSINESS_KEY)
    parser.add_argument("--smoke-only", action="store_true")
    return parser.parse_args()


def parse_scale_list(raw: str) -> list[int]:
    values = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise ValueError("target scales cannot be empty")
    return values


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def build_headers(*, api_key: str, anthropic: bool = False) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if anthropic:
        headers["anthropic-version"] = "2023-06-01"
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    return headers


def resolve_root_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    return normalized[:-3] if normalized.endswith("/v1") else normalized


def resolve_endpoint(base_url: str) -> str:
    config = AIProviderConfig(
        provider="codex2gpt",
        base_url=base_url,
        api_key=None,
        model="unused",
        timeout_seconds=30,
    )
    resolved = _resolve_local_base_url(
        config=config,
        default_base_url=DEFAULT_CODEX2GPT_BASE_URL,
        provider_label="codex2gpt",
    )
    return f"{resolved}/chat/completions"


def load_health(root_url: str) -> dict[str, Any]:
    with httpx.Client(timeout=15) as client:
        response = client.get(f"{root_url}/health")
        response.raise_for_status()
        return response.json()


def resolve_count_tokens_model(requested_model: str, override: str) -> str:
    if override.strip():
        return override.strip()
    mapping = {
        "gpt-5.4": "claude-sonnet-4-6",
        "gpt-5.4-1m": "claude-opus-4-6",
        "gpt-5.3-codex": "claude-haiku-4-5",
    }
    return mapping.get(requested_model, "claude-sonnet-4-6")


def estimate_input_tokens(
    *,
    base_url: str,
    api_key: str,
    count_tokens_model: str,
    instructions: str,
    serialized_payload: str,
    timeout: int,
) -> tuple[int | None, str | None]:
    payload = {
        "model": count_tokens_model,
        "max_tokens": 1,
        "messages": [
            {
                "role": "user",
                "content": (
                    "[system]\n"
                    f"{instructions}\n\n"
                    "[payload_json]\n"
                    f"{serialized_payload}"
                ),
            }
        ],
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url.rstrip('/')}/messages/count_tokens",
                json=payload,
                headers=build_headers(api_key=api_key, anthropic=True),
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    value = data.get("input_tokens")
    if isinstance(value, int):
        return value, None
    return None, "count_tokens returned no input_tokens"


def split_blocks(text: str) -> list[str]:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    return blocks or [text.strip()]


def join_filler(blocks: list[str], repeat_count: int) -> str:
    if repeat_count <= 0:
        return ""
    parts: list[str] = []
    for repeat_index in range(1, repeat_count + 1):
        for block_index, block in enumerate(blocks, start=1):
            parts.append(f"[filler block {block_index} repeat {repeat_index}]\n{block}")
    return "\n\n".join(parts).strip()


def extract_job_keywords(job_text: str) -> list[str]:
    seed = []
    for token in (
        "FastAPI",
        "Python",
        "Next.js",
        "TypeScript",
        "structured output",
        "JSON validation",
        "streaming",
        "context limit",
        "resume workflow",
        "mock interview",
    ):
        if token.lower() in job_text.lower():
            seed.append(token)
    return seed[:12]


def summarize_markdown(markdown: str, char_limit: int) -> str:
    normalized = markdown.strip()
    if len(normalized) <= char_limit:
        return normalized
    return normalized[:char_limit].rstrip() + "\n..."


def base_resume_data(resume_file: str, jd_file: str, filler_file: str) -> dict[str, Any]:
    resume_markdown = read_text(resume_file)
    job_description = read_text(jd_file)
    filler_blocks = split_blocks(read_text(filler_file))
    structured_resume = parse_resume_markdown(resume_markdown)
    canonical_markdown = render_resume_markdown(structured_resume).strip()
    return {
        "resume_markdown": resume_markdown,
        "job_description": job_description,
        "filler_blocks": filler_blocks,
        "structured_resume": structured_resume,
        "canonical_markdown": canonical_markdown,
        "job_keywords": extract_job_keywords(job_description),
    }


def get_prompt_groups(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    b2_resume_md = summarize_markdown(data["canonical_markdown"], 2400)
    return {
        "simple_prompt": {
            "label": "A组 简单提示词",
            "complexity": "simple",
            "output_kind": "plain_text",
            "instructions": (
                "你是一个简洁的中文助手。"
                "阅读 user JSON 中的 question 和 context，"
                "只用中文输出 2 句简短回答。不要输出 JSON，不要分点。"
            ),
            "builder": lambda filler: {
                "question": "请用中文简要解释什么是上下文窗口，以及为什么流式接口可能在复杂请求下更脆弱？",
                "context": filler,
            },
        },
        "complex_prompt_b1": {
            "label": "B1 复杂指令但无重结构输入",
            "complexity": "complex_b1",
            "output_kind": "markdown",
            "instructions": (
                "你是一个流式接口分析助手。你会收到一段背景文本。"
                "请输出结构化 Markdown，并且必须包含以下一级标题：结论、关键信号、风险、建议。"
                "每个标题下至少写 2 句具体内容。不要输出 JSON。"
            ),
            "builder": lambda filler: {
                "task_name": "stream_probe_b1",
                "analysis_goal": "分析流式接口在长上下文下的潜在风险",
                "background": filler,
                "required_sections": ["结论", "关键信号", "风险", "建议"],
            },
        },
        "complex_prompt_b2": {
            "label": "B2 复杂指令 + 中等结构化输入",
            "complexity": "complex_b2",
            "output_kind": "json",
            "instructions": (
                "你是一个岗位匹配分析助手。"
                "你会收到 job_description、job_keywords、resume_markdown、background_context。"
                "只输出一个 JSON object，字段固定为："
                "summary(string), matchedKeywords(array), risks(array), suggestions(array)。"
                "不要输出额外文本。"
            ),
            "builder": lambda filler: {
                "task_name": "stream_probe_b2",
                "output_language": "zh-CN",
                "job_description": data["job_description"],
                "job_keywords": data["job_keywords"],
                "resume_markdown": b2_resume_md,
                "background_context": filler,
            },
        },
        "complex_prompt_b3": {
            "label": "B3 真实业务重载链路",
            "complexity": "complex_b3",
            "output_kind": "tailored_resume_document",
            "instructions": get_tailored_resume_full_document_prompt(),
            "builder": lambda filler: {
                "output_language": "zh-CN",
                "job_description": (
                    data["job_description"]
                    if not filler
                    else f"{data['job_description']}\n\n[additional_context]\n{filler}"
                ),
                "job_keywords": data["job_keywords"],
                "original_resume_json": data["structured_resume"].model_dump(mode="json"),
                "original_resume_markdown": data["canonical_markdown"],
                "optimization_level": "conservative",
            },
        },
    }


def fit_repeat_count(
    *,
    group_id: str,
    target_scale_tokens: int,
    group: dict[str, Any],
    filler_blocks: list[str],
    base_url: str,
    api_key: str,
    count_tokens_model: str,
    timeout: int,
) -> BuiltRequest:
    filler_unit = join_filler(filler_blocks, 1)
    filler_unit_chars = max(1, len(filler_unit))

    base_payload = group["builder"]("")
    base_serialized = json.dumps(base_payload, ensure_ascii=False)
    base_input_chars = len(group["instructions"]) + len(base_serialized)
    approx_target_chars = target_scale_tokens * 4
    approx_repeat_count = 0
    if group_id != "complex_prompt_b3" and approx_target_chars > base_input_chars:
        approx_repeat_count = max(0, round((approx_target_chars - base_input_chars) / filler_unit_chars))

    filler = join_filler(filler_blocks, approx_repeat_count)
    payload = group["builder"](filler)
    serialized = json.dumps(payload, ensure_ascii=False)
    estimated, token_error = estimate_input_tokens(
        base_url=base_url,
        api_key=api_key,
        count_tokens_model=count_tokens_model,
        instructions=group["instructions"],
        serialized_payload=serialized,
        timeout=min(timeout, 45),
    )
    return BuiltRequest(
        instructions=group["instructions"],
        payload=payload,
        estimated_input_tokens=estimated,
        estimated_input_tokens_error=token_error,
        input_chars=len(group["instructions"]) + len(serialized),
        payload_chars=len(serialized),
        filler_repeat_count=approx_repeat_count,
        target_scale_tokens=target_scale_tokens,
    )


def parse_sse_response(response: httpx.Response, *, request_started_at: float) -> dict[str, Any]:
    raw_lines: list[str] = []
    delta_chunks: list[str] = []
    done_received = False
    finish_reason: str | None = None
    first_token_at: float | None = None
    last_token_at: float | None = None

    for raw_line in response.iter_lines():
        now = perf_counter()
        if raw_line is None:
            continue
        line = raw_line.strip()
        if not line:
            continue
        raw_lines.append(line)
        if not line.startswith("data: "):
            continue
        payload_text = line[6:].strip()
        if payload_text == "[DONE]":
            done_received = True
            last_token_at = last_token_at or now
            continue
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            return {
                "classification": "parse_error",
                "error_type": "parse_error",
                "error_message": f"SSE JSON decode failed: {exc.msg}",
                "raw_response_preview": _build_response_preview("\n".join(raw_lines)),
                "text": "",
                "chunk_count": len(delta_chunks),
                "received_done": done_received,
                "finish_reason": finish_reason,
                "time_to_first_token_ms": None if first_token_at is None else round((first_token_at - request_started_at) * 1000, 1),
                "time_to_last_token_ms": None if last_token_at is None else round((last_token_at - request_started_at) * 1000, 1),
            }
        choices = payload.get("choices")
        first_choice = (
            choices[0]
            if isinstance(choices, list) and choices and isinstance(choices[0], dict)
            else None
        )
        if first_choice is None:
            continue
        choice_finish_reason = first_choice.get("finish_reason")
        if isinstance(choice_finish_reason, str) and choice_finish_reason.strip():
            finish_reason = choice_finish_reason.strip()
        delta = first_choice.get("delta")
        if not isinstance(delta, dict):
            continue
        content = delta.get("content")
        text_chunk = ""
        if isinstance(content, str):
            text_chunk = content
        elif isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            text_chunk = "".join(parts)
        if text_chunk:
            if first_token_at is None:
                first_token_at = now
            last_token_at = now
            delta_chunks.append(text_chunk)

    text = "".join(delta_chunks).strip()
    classification = "success_candidate"
    error_type = ""
    error_message = ""
    if not text:
        classification = "empty_output" if done_received else "stream_broken"
        error_type = classification
        error_message = (
            "stream completed without usable text"
            if done_received
            else "stream ended before [DONE] and no usable assistant text was recovered"
        )
    elif not done_received:
        classification = "stream_broken"
        error_type = "stream_broken"
        error_message = "assistant text arrived but the stream ended before [DONE]"

    return {
        "classification": classification,
        "error_type": error_type,
        "error_message": error_message,
        "raw_response_preview": _build_response_preview("\n".join(raw_lines)),
        "text": text,
        "chunk_count": len(delta_chunks),
        "received_done": done_received,
        "finish_reason": finish_reason,
        "time_to_first_token_ms": None if first_token_at is None else round((first_token_at - request_started_at) * 1000, 1),
        "time_to_last_token_ms": None if last_token_at is None else round((last_token_at - request_started_at) * 1000, 1),
    }


def classify_output(group_id: str, text: str, finish_reason: str | None) -> tuple[str, bool, list[str], dict[str, Any]]:
    reasons: list[str] = []
    details: dict[str, Any] = {}
    normalized = text.strip()
    if not normalized:
        return "empty_output", False, ["assistant_text_empty"], details

    if group_id == "simple_prompt":
        details["output_chars"] = len(normalized)
        if len(normalized) < 20:
            reasons.append("output_too_short")
        if finish_reason == "length":
            reasons.append("finish_reason_length")
        return ("success_but_weak" if reasons else "success_usable"), not reasons, reasons, details

    if group_id == "complex_prompt_b1":
        details["output_chars"] = len(normalized)
        heading_hits = sum(1 for heading in ("# 结论", "# 关键信号", "# 风险", "# 建议") if heading in normalized)
        details["heading_hits"] = heading_hits
        if heading_hits < 3:
            reasons.append("missing_required_headings")
        if len(normalized) < 180:
            reasons.append("output_too_short")
        if finish_reason == "length":
            reasons.append("finish_reason_length")
        return ("success_but_weak" if reasons else "success_usable"), not reasons, reasons, details

    if group_id == "complex_prompt_b2":
        try:
            payload = json.loads(_extract_json_object(normalized))
        except Exception as exc:  # noqa: BLE001
            details["validation_error"] = str(exc)
            return "parse_error", False, ["json_parse_failed"], details
        if not isinstance(payload, dict):
            return "parse_error", False, ["json_root_not_object"], details
        for key in ("summary", "matchedKeywords", "risks", "suggestions"):
            if key not in payload:
                reasons.append(f"missing_{key}")
        summary_text = str(payload.get("summary") or "").strip()
        risks = payload.get("risks") if isinstance(payload.get("risks"), list) else []
        suggestions = payload.get("suggestions") if isinstance(payload.get("suggestions"), list) else []
        details["summary_chars"] = len(summary_text)
        details["risks_count"] = len(risks)
        details["suggestions_count"] = len(suggestions)
        if len(summary_text) < 40:
            reasons.append("summary_too_short")
        if len(risks) < 2:
            reasons.append("risks_too_few")
        if len(suggestions) < 2:
            reasons.append("suggestions_too_few")
        if finish_reason == "length":
            reasons.append("finish_reason_length")
        return ("success_but_weak" if reasons else "success_usable"), not reasons, reasons, details

    if group_id == "complex_prompt_b3":
        try:
            payload = json.loads(_extract_json_object(normalized))
            document = TailoredResumeDocument.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            details["validation_error"] = str(exc)
            return "invalid_business_output", False, ["tailored_resume_validation_failed"], details
        markdown = document.markdown.strip()
        details["markdown_chars"] = len(markdown)
        details["experience_count"] = len(document.experience)
        details["project_count"] = len(document.projects)
        if len(markdown) < 300:
            reasons.append("markdown_too_short")
        if len(document.experience) < 1:
            reasons.append("experience_items_too_few")
        if len(document.projects) < 1:
            reasons.append("project_items_too_few")
        if finish_reason == "length":
            reasons.append("finish_reason_length")
        return ("success_but_weak" if reasons else "success_usable"), not reasons, reasons, details

    return "parse_error", False, ["unknown_group"], details


def run_probe_once(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    timeout: int,
    client_id: str,
    business_key: str,
    group_id: str,
    built: BuiltRequest,
) -> dict[str, Any]:
    serialized_payload = json.dumps(built.payload, ensure_ascii=False)
    request_body = {
        "model": model,
        "stream": True,
        "client_id": client_id,
        "business_key": business_key,
        "messages": [
            {"role": "system", "content": built.instructions},
            {"role": "user", "content": serialized_payload},
        ],
        "max_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
    }
    result: dict[str, Any] = {
        "group_id": group_id,
        "target_scale_tokens": built.target_scale_tokens,
        "filler_repeat_count": built.filler_repeat_count,
        "input_chars": built.input_chars,
        "payload_chars": built.payload_chars,
        "estimated_input_tokens": built.estimated_input_tokens,
        "estimated_input_tokens_error": built.estimated_input_tokens_error,
        "classification": "",
        "usable": False,
        "time_to_first_token_ms": None,
        "time_to_last_token_ms": None,
        "received_done": False,
        "chunk_count": 0,
        "output_chars": 0,
        "finish_reason": None,
        "error_type": "",
        "error_message": "",
        "http_status_code": None,
        "seconds": None,
        "quality_reasons": [],
        "raw_response_preview": "",
        "validation_details": {},
    }

    started_at = perf_counter()
    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "POST",
                endpoint,
                json=request_body,
                headers=build_headers(api_key=api_key),
            ) as response:
                result["http_status_code"] = response.status_code
                response.raise_for_status()
                parsed = parse_sse_response(response, request_started_at=started_at)
        result["seconds"] = round(perf_counter() - started_at, 2)
        result["time_to_first_token_ms"] = parsed["time_to_first_token_ms"]
        result["time_to_last_token_ms"] = parsed["time_to_last_token_ms"]
        result["received_done"] = parsed["received_done"]
        result["chunk_count"] = parsed["chunk_count"]
        result["finish_reason"] = parsed["finish_reason"]
        result["raw_response_preview"] = parsed["raw_response_preview"]
        text = parsed["text"]
        result["output_chars"] = len(text)
        if parsed["classification"] != "success_candidate":
            result["classification"] = parsed["classification"]
            result["error_type"] = parsed["error_type"] or parsed["classification"]
            result["error_message"] = parsed["error_message"]
            return result
        classification, usable, quality_reasons, validation_details = classify_output(
            group_id,
            text,
            parsed["finish_reason"],
        )
        result["classification"] = classification
        result["usable"] = usable
        result["quality_reasons"] = quality_reasons
        result["validation_details"] = validation_details
        if classification not in SUCCESS_CLASSIFICATIONS:
            result["error_type"] = classification
            result["error_message"] = validation_details.get("validation_error", "")
        return result
    except httpx.TimeoutException as exc:
        result["seconds"] = round(perf_counter() - started_at, 2)
        result["classification"] = "timeout"
        result["error_type"] = "timeout"
        result["error_message"] = str(exc)
        return result
    except httpx.HTTPStatusError as exc:
        result["seconds"] = round(perf_counter() - started_at, 2)
        result["classification"] = "http_error"
        result["error_type"] = f"http_{exc.response.status_code}"
        raw_error = ""
        try:
            raw_error = exc.response.read().decode("utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001
            raw_error = ""
        result["error_message"] = raw_error or str(exc)
        result["http_status_code"] = exc.response.status_code
        result["raw_response_preview"] = _build_response_preview(raw_error)
        return result
    except (httpx.RequestError, socket.timeout, TimeoutError) as exc:
        result["seconds"] = round(perf_counter() - started_at, 2)
        result["classification"] = "stream_broken"
        result["error_type"] = exc.__class__.__name__
        result["error_message"] = str(exc)
        return result
    except Exception as exc:  # noqa: BLE001
        result["seconds"] = round(perf_counter() - started_at, 2)
        result["classification"] = "parse_error"
        result["error_type"] = exc.__class__.__name__
        result["error_message"] = str(exc)
        return result


def summarize_group(group_id: str, group_runs: list[dict[str, Any]]) -> dict[str, Any]:
    usable_runs = [run for run in group_runs if run["classification"] == "success_usable"]
    success_runs = [run for run in group_runs if run["classification"] in SUCCESS_CLASSIFICATIONS]
    failure_runs = [run for run in group_runs if run["classification"] not in SUCCESS_CLASSIFICATIONS]
    phase_probe_runs = [run for run in group_runs if run["phase"] == "probe"]
    first_success = next((run for run in phase_probe_runs if run["classification"] == "success_usable"), None)
    first_failure = next((run for run in phase_probe_runs if run["classification"] not in SUCCESS_CLASSIFICATIONS), None)
    max_usable = max(
        usable_runs,
        key=lambda run: (run["estimated_input_tokens"] or 0, run["target_scale_tokens"]),
        default=None,
    )
    seconds_values = [float(run["seconds"]) for run in group_runs if run["seconds"] is not None]
    error_counter = Counter(run["error_type"] or run["classification"] for run in failure_runs)
    main_error_type = error_counter.most_common(1)[0][0] if error_counter else ""
    return {
        "group_id": group_id,
        "first_success_point": compact_run_point(first_success),
        "first_failure_point": compact_run_point(first_failure),
        "max_usable_success": compact_run_point(max_usable),
        "main_error_type": main_error_type,
        "success_rate": round(len(success_runs) / len(group_runs), 4) if group_runs else 0.0,
        "usable_success_rate": round(len(usable_runs) / len(group_runs), 4) if group_runs else 0.0,
        "avg_seconds": round(sum(seconds_values) / len(seconds_values), 2) if seconds_values else None,
        "p50_seconds": round(statistics.median(seconds_values), 2) if seconds_values else None,
        "max_seconds": round(max(seconds_values), 2) if seconds_values else None,
        "probe_run_count": len(phase_probe_runs),
        "total_run_count": len(group_runs),
    }


def compact_run_point(run: dict[str, Any] | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "target_scale_tokens": run.get("target_scale_tokens"),
        "estimated_input_tokens": run.get("estimated_input_tokens"),
        "input_chars": run.get("input_chars"),
        "classification": run.get("classification"),
        "usable": run.get("usable"),
        "time_to_first_token_ms": run.get("time_to_first_token_ms"),
        "time_to_last_token_ms": run.get("time_to_last_token_ms"),
        "received_done": run.get("received_done"),
        "chunk_count": run.get("chunk_count"),
        "output_chars": run.get("output_chars"),
        "finish_reason": run.get("finish_reason"),
        "error_type": run.get("error_type"),
        "error_message": run.get("error_message"),
        "seconds": run.get("seconds"),
    }


def pick_followup_group(group_summaries: dict[str, dict[str, Any]]) -> str | None:
    for group_id in ("complex_prompt_b3", "complex_prompt_b2", "complex_prompt_b1", "simple_prompt"):
        summary = group_summaries.get(group_id)
        if not summary:
            continue
        if (
            summary["max_usable_success"]
            and summary["first_failure_point"]
            and (summary["max_usable_success"]["estimated_input_tokens"] or 0)
            < (summary["first_failure_point"]["estimated_input_tokens"] or 0)
        ):
            return group_id
    for group_id in ("complex_prompt_b3", "complex_prompt_b2", "complex_prompt_b1", "simple_prompt"):
        summary = group_summaries.get(group_id)
        if summary and summary["max_usable_success"]:
            return group_id
    return None


def build_summary(group_summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    simple = group_summaries["simple_prompt"]
    b1 = group_summaries["complex_prompt_b1"]
    b2 = group_summaries["complex_prompt_b2"]
    b3 = group_summaries["complex_prompt_b3"]
    worthy = pick_followup_group(group_summaries)
    simple_fail = simple["first_failure_point"]["estimated_input_tokens"] if simple["first_failure_point"] else None
    b3_fail = b3["first_failure_point"]["estimated_input_tokens"] if b3["first_failure_point"] else None
    if simple["max_usable_success"] is None and any(
        group_summaries[group_id]["max_usable_success"] is not None
        for group_id in ("complex_prompt_b1", "complex_prompt_b2", "complex_prompt_b3")
    ):
        successful_groups = [
            group_id
            for group_id in ("complex_prompt_b1", "complex_prompt_b2", "complex_prompt_b3")
            if group_summaries[group_id]["max_usable_success"] is not None
        ]
        complexity_difference = (
            "简单 prompt 并没有天然更稳。当前样本里，simple_prompt 在约 "
            f"{simple_fail} tokens 就以 partial stream 形式断掉，"
            f"而 {', '.join(successful_groups)} 至少各出现过一次完整 success_usable。"
        )
    elif simple_fail is not None and b3_fail is not None and simple_fail > b3_fail:
        complexity_difference = (
            f"简单提示词首次失败约在 {simple_fail} tokens，"
            f"B3 首次失败约在 {b3_fail} tokens；复杂度越高越早断流。"
        )
    else:
        complexity_difference = (
            "复杂度不是唯一变量。当前更像是“输出形态 + 响应时长 + 流式稳定性”共同影响结果；"
            "需要继续在存在成功区间的组上做临界点复测。"
        )
    recommendation = (
        "当前 stream=true 还不适合直接把真实长 JSON 链路当作稳定方案。"
        "B1 有清晰成功区间，适合下一轮做临界点复测与稳定上限测量；"
        "B3 更像排障对象，因为它要么首档即断流，要么单次成功但 TTFT/总耗时极高。"
    )
    return {
        "simple_prompt_overall": {
            "first_success_point": simple["first_success_point"],
            "first_failure_point": simple["first_failure_point"],
            "main_error_type": simple["main_error_type"],
        },
        "complex_prompt_overall": {
            "complex_prompt_b1": {
                "first_success_point": b1["first_success_point"],
                "first_failure_point": b1["first_failure_point"],
                "main_error_type": b1["main_error_type"],
            },
            "complex_prompt_b2": {
                "first_success_point": b2["first_success_point"],
                "first_failure_point": b2["first_failure_point"],
                "main_error_type": b2["main_error_type"],
            },
            "complex_prompt_b3": {
                "first_success_point": b3["first_success_point"],
                "first_failure_point": b3["first_failure_point"],
                "main_error_type": b3["main_error_type"],
            },
        },
        "prompt_complexity_difference": complexity_difference,
        "stream_engineering_recommendation": recommendation,
        "worthy_group_for_stability_followup": worthy,
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: str | Path, runs: list[dict[str, Any]]) -> None:
    fieldnames = [
        "group_id",
        "phase",
        "attempt_index",
        "target_scale_tokens",
        "estimated_input_tokens",
        "filler_repeat_count",
        "input_chars",
        "payload_chars",
        "classification",
        "usable",
        "time_to_first_token_ms",
        "time_to_last_token_ms",
        "received_done",
        "chunk_count",
        "output_chars",
        "finish_reason",
        "error_type",
        "error_message",
        "seconds",
        "http_status_code",
        "quality_reasons",
    ]
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            row = {name: run.get(name) for name in fieldnames}
            row["quality_reasons"] = ",".join(run.get("quality_reasons", []))
            writer.writerow(row)


def render_group_line(group_id: str, summary: dict[str, Any]) -> list[str]:
    label_map = {
        "simple_prompt": "simple_prompt",
        "complex_prompt_b1": "complex_prompt_b1",
        "complex_prompt_b2": "complex_prompt_b2",
        "complex_prompt_b3": "complex_prompt_b3",
    }
    first_success = summary["first_success_point"]
    first_failure = summary["first_failure_point"]
    max_usable = summary["max_usable_success"]
    return [
        f"### {label_map[group_id]}",
        f"- first_success_point: {first_success['estimated_input_tokens'] if first_success else None}",
        f"- first_failure_point: {first_failure['estimated_input_tokens'] if first_failure else None}",
        f"- max_usable_success: {max_usable['estimated_input_tokens'] if max_usable else None}",
        f"- main_error_type: {summary['main_error_type'] or '-'}",
        f"- success_rate: {summary['success_rate']}",
        "",
    ]


def build_report_markdown(output: dict[str, Any]) -> str:
    lines = [
        "# codex2gpt stream=true prompt complexity probe",
        "",
        "## 一眼结论",
        "",
    ]
    for group_id in ("simple_prompt", "complex_prompt_b1", "complex_prompt_b2", "complex_prompt_b3"):
        lines.extend(render_group_line(group_id, output["group_summaries"][group_id]))
    lines.extend(
        [
            "## 差异判断",
            "",
            f"- {output['summary']['prompt_complexity_difference']}",
            f"- 值得继续做稳定上限测试的组：{output['summary']['worthy_group_for_stability_followup']}",
            "",
            "## 工程建议",
            "",
            f"- {output['summary']['stream_engineering_recommendation']}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    target_scales = parse_scale_list(args.sample_scales if args.smoke_only else args.target_scales)
    base_url = args.base_url.rstrip("/")
    root_url = resolve_root_url(base_url)
    endpoint = resolve_endpoint(base_url)
    health = load_health(root_url)
    count_tokens_model = resolve_count_tokens_model(args.model, args.count_tokens_model)
    data = base_resume_data(args.resume_file, args.jd_file, args.filler_file)
    prompt_groups = get_prompt_groups(data)

    print(f"base_url={base_url}")
    print(f"model={args.model}")
    print(f"endpoint={endpoint}")
    print(f"target_scales={target_scales}")

    all_runs: list[dict[str, Any]] = []
    group_runs: dict[str, list[dict[str, Any]]] = {group_id: [] for group_id in prompt_groups}

    for group_id in ("simple_prompt", "complex_prompt_b1", "complex_prompt_b2", "complex_prompt_b3"):
        group = prompt_groups[group_id]
        first_failure_run: dict[str, Any] | None = None
        last_success_run: dict[str, Any] | None = None
        for scale in target_scales:
            built = fit_repeat_count(
                group_id=group_id,
                target_scale_tokens=scale,
                group=group,
                filler_blocks=data["filler_blocks"],
                base_url=base_url,
                api_key=args.api_key,
                count_tokens_model=count_tokens_model,
                timeout=args.timeout,
            )
            run = run_probe_once(
                endpoint=endpoint,
                api_key=args.api_key,
                model=args.model,
                timeout=args.timeout,
                client_id=args.client_id,
                business_key=args.business_key,
                group_id=group_id,
                built=built,
            )
            run["phase"] = "probe"
            run["attempt_index"] = 1
            all_runs.append(run)
            group_runs[group_id].append(run)
            print(
                f"[{group_id}] target={scale} est={run['estimated_input_tokens']} "
                f"classification={run['classification']} first_token_ms={run['time_to_first_token_ms']} "
                f"done={run['received_done']} error={run['error_type']}"
            )
            if run["classification"] in SUCCESS_CLASSIFICATIONS:
                if run["classification"] == "success_usable":
                    last_success_run = run
                continue
            first_failure_run = run
            break

    group_summaries = {
        group_id: summarize_group(group_id, runs)
        for group_id, runs in group_runs.items()
    }
    summary = build_summary(group_summaries)
    output = {
        "metadata": {
            "generated_at": datetime.now(UTC).isoformat(),
            "script": str(Path(__file__).resolve()),
            "career_pilot_root": str(ROOT),
            "transport_backend": health.get("transport_backend"),
        },
        "probe_settings": {
            "base_url": base_url,
            "endpoint": endpoint,
            "model": args.model,
            "count_tokens_model": count_tokens_model,
            "stream": True,
            "target_scales_tokens": target_scales,
            "timeout": args.timeout,
            "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
            "resume_file": str(Path(args.resume_file).resolve()),
            "jd_file": str(Path(args.jd_file).resolve()),
            "filler_file": str(Path(args.filler_file).resolve()),
        },
        "prompt_groups": {
            group_id: {
                "label": group["label"],
                "complexity": group["complexity"],
                "output_kind": group["output_kind"],
            }
            for group_id, group in prompt_groups.items()
        },
        "runs": all_runs,
        "group_summaries": group_summaries,
        "summary": summary,
    }
    write_json(args.json_out, output)
    write_csv(args.csv_out, all_runs)
    Path(args.report_out).write_text(build_report_markdown(output), encoding="utf-8")


if __name__ == "__main__":
    main()
