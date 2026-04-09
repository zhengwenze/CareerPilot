import asyncio
import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from app.prompts.resume import get_resume_pdf_to_md_prompt
from app.services.ai_client import AIClientError, AIProviderConfig, request_text_completion
from app.services.resume_ai import is_ai_configured

logger = logging.getLogger(__name__)
PROMPT_VERSION = "resume_pdf_to_md_v2"

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(
    r"(https?://[^\s)>\]]+|www\.[^\s)>\]]+|linkedin\.com/[^\s)>\]]+|github\.com/[^\s)>\]]+)",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?:(?:\+?\d[\d\s().-]{6,}\d))")
DATE_TOKEN_PATTERN = re.compile(
    r"(\b\d{4}[./-]\d{1,2}\b|\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b|\b\d{4}年\d{1,2}月?\b)",
    re.IGNORECASE,
)
SECTION_SIGNAL_GROUPS = {
    "education": ("教育经历", "教育背景", "education"),
    "work": ("工作经历", "工作经验", "work experience", "experience"),
    "projects": ("项目经历", "项目经验", "project experience", "projects"),
    "skills": ("专业技能", "技能", "skills"),
}


@dataclass(frozen=True, slots=True)
class PdfToMarkdownAttempt:
    provider: str
    model: str
    stage: str
    status: str
    latency_ms: int | None
    error: str | None


@dataclass(frozen=True, slots=True)
class PdfToMarkdownResult:
    markdown: str
    raw_markdown: str
    cleaned_markdown: str
    ai_used: bool
    ai_provider: str
    ai_model: str
    ai_error: str | None
    fallback_used: bool
    prompt_version: str
    ai_latency_ms: int | None
    ai_path: str
    ai_attempts: list[PdfToMarkdownAttempt]
    ai_chain_latency_ms: int | None
    degraded_used: bool
    configured_primary_provider: str = ""
    configured_primary_model: str = ""
    configured_secondary_provider: str = ""
    configured_secondary_model: str = ""
    last_attempt_status: str = ""
    ai_error_category: str | None = None

    @property
    def ai_applied(self) -> bool:
        return self.ai_used

    @property
    def ai_error_message(self) -> str | None:
        return self.ai_error


def normalize_markdown(markdown: str) -> str:
    lines = [line.rstrip() for line in markdown.splitlines()]
    cleaned: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        cleaned.append(line)
        previous_blank = is_blank
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return "\n".join(cleaned).strip()


def build_pdf_to_md_user_prompt(raw_markdown: str) -> str:
    return f"""下面是从 PDF 简历中提取出来的原始 Markdown，请你整理成最终简历 Markdown。

请特别注意：
- 这是"高保真转换"任务，不是"润色改写"任务
- 严禁编造、补充、猜测任何输入里不存在的事实
- 必须完整保留邮箱、电话、URL、时间、公司名、学校名
- 必须完整保留项目链接、仓库链接、个人主页链接
- 如果你发现项目标题附近存在 URL，请务必保留到最终输出中
- 只允许优化标题层级、列表格式、空行和段落结构
- 优先保留信息，不要为了美观省略内容
- 如果原始 Markdown 已经较好，只做最小必要清洗

请直接输出最终 Markdown，不要输出解释。

---------------- RAW MARKDOWN BEGIN ----------------
{raw_markdown}
---------------- RAW MARKDOWN END ----------------
"""


def extract_raw_markdown_from_pdf(pdf_bytes: bytes, file_name: str) -> str:
    try:
        import pymupdf4llm
    except ImportError:
        logger.exception("resume-pdf-to-md missing dependency pymupdf4llm file=%s", file_name)
        return ""

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        raw_markdown = pymupdf4llm.to_markdown(tmp_path)
    except Exception:
        logger.exception("resume-pdf-to-md failed during raw markdown extraction file=%s", file_name)
        return ""
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    normalized = normalize_markdown(raw_markdown)
    if not normalized:
        logger.warning("resume-pdf-to-md extracted empty markdown file=%s", file_name)
        return ""
    return normalized


def _provider_parts(config: AIProviderConfig | None) -> tuple[str, str]:
    return (
        (getattr(config, "provider", "") or "").strip().lower(),
        (getattr(config, "model", "") or "").strip(),
    )


def _build_skipped_attempt(
    *,
    stage: str,
    config: AIProviderConfig | None,
    error: str | None = None,
) -> PdfToMarkdownAttempt:
    provider, model = _provider_parts(config)
    return PdfToMarkdownAttempt(
        provider=provider,
        model=model,
        stage=stage,
        status="skipped",
        latency_ms=None,
        error=error,
    )


def _normalize_url_token(token: str) -> str:
    return token.rstrip(".,);]>").strip().lower()


def _extract_urls(text: str) -> set[str]:
    return {
        _normalize_url_token(match.group(0))
        for match in URL_PATTERN.finditer(text)
        if _normalize_url_token(match.group(0))
    }


def _extract_emails(text: str) -> set[str]:
    return {match.group(0).lower() for match in EMAIL_PATTERN.finditer(text)}


def _normalize_phone_token(token: str) -> str:
    digits = re.sub(r"\D+", "", token)
    return digits if 7 <= len(digits) <= 16 else ""


def _extract_phones(text: str) -> set[str]:
    values: set[str] = set()
    for match in PHONE_PATTERN.finditer(text):
        normalized = _normalize_phone_token(match.group(0))
        if normalized:
            values.add(normalized)
    return values


def _extract_date_token_count(text: str) -> int:
    return len(DATE_TOKEN_PATTERN.findall(text))


def _missing_values(raw_values: set[str], cleaned_values: set[str]) -> list[str]:
    return sorted(value for value in raw_values if value not in cleaned_values)


def _has_section_signal(text: str, section_names: tuple[str, ...]) -> bool:
    lower_text = text.lower()
    return any(section.lower() in lower_text for section in section_names)


def validate_markdown_quality(raw_markdown: str, cleaned_markdown: str) -> str | None:
    raw_emails = _extract_emails(raw_markdown)
    missing_emails = _missing_values(raw_emails, _extract_emails(cleaned_markdown))
    if missing_emails:
        return f"AI output removed email(s): {', '.join(missing_emails[:3])}"

    raw_phones = _extract_phones(raw_markdown)
    missing_phones = _missing_values(raw_phones, _extract_phones(cleaned_markdown))
    if missing_phones:
        return f"AI output removed phone number(s): {', '.join(missing_phones[:3])}"

    raw_urls = _extract_urls(raw_markdown)
    missing_urls = _missing_values(raw_urls, _extract_urls(cleaned_markdown))
    if missing_urls:
        return f"AI output removed URL(s): {', '.join(missing_urls[:3])}"

    for section_name, section_signals in SECTION_SIGNAL_GROUPS.items():
        if _has_section_signal(raw_markdown, section_signals) and not _has_section_signal(
            cleaned_markdown, section_signals
        ):
            return f"AI output removed required section: {section_name}"

    raw_date_tokens = _extract_date_token_count(raw_markdown)
    if raw_date_tokens >= 2:
        cleaned_date_tokens = _extract_date_token_count(cleaned_markdown)
        if cleaned_date_tokens < max(1, int(raw_date_tokens * 0.7)):
            return (
                "AI output removed too many date tokens: "
                f"raw={raw_date_tokens} cleaned={cleaned_date_tokens}"
            )

    return None


def _attempt_status_from_category(category: str | None) -> str:
    normalized = (category or "").strip().lower()
    if normalized == "timeout":
        return "timeout"
    if normalized == "http_502_upstream_disconnect":
        return "upstream_disconnect"
    if normalized == "connection_error":
        return "connection_error"
    if normalized == "quality_guard_failed":
        return "quality_guard_failed"
    if normalized == "invalid_response_format":
        return "invalid_response_format"
    if normalized == "json_decode_error":
        return "invalid_output"
    if normalized.startswith("http_") or normalized in {
        "auth_error",
        "permission_error",
        "provider_error",
        "config_error",
    }:
        return "http_error"
    return "invalid_output"


async def _run_ai_attempt(
    *,
    stage: str,
    file_name: str,
    raw_markdown: str,
    ai_config: AIProviderConfig | None,
    retry_count_override: int,
    total_timeout_budget_seconds: float | None = None,
) -> tuple[PdfToMarkdownAttempt, str | None, str | None]:
    provider, model = _provider_parts(ai_config)
    if ai_config is None or not is_ai_configured(
        provider=ai_config.provider,
        base_url=ai_config.base_url,
        model=ai_config.model,
        api_key=ai_config.api_key,
    ):
        logger.warning(
            "resume-pdf-to-md AI stage skipped due to incomplete config "
            "file=%s stage=%s provider=%s model=%s base_url=%s",
            file_name,
            stage,
            getattr(ai_config, "provider", ""),
            getattr(ai_config, "model", ""),
            getattr(ai_config, "base_url", ""),
        )
        return (
            _build_skipped_attempt(
                stage=stage,
                config=ai_config,
                error="AI config incomplete",
            ),
            None,
            "config_error",
        )

    request_started = perf_counter()
    try:
        markdown = await request_text_completion(
            config=ai_config,
            instructions=get_resume_pdf_to_md_prompt(),
            payload={
                "raw_markdown": raw_markdown,
                "user_prompt": build_pdf_to_md_user_prompt(raw_markdown),
            },
            max_tokens=4000,
            retry_count_override=retry_count_override,
            total_timeout_budget_seconds=total_timeout_budget_seconds,
        )
        latency_ms = max(0, int((perf_counter() - request_started) * 1000))
        normalized_markdown = normalize_markdown(markdown)
        if not normalized_markdown:
            raise AIClientError(
                category="invalid_response_format",
                detail="AI response was empty after Markdown normalization",
            )

        quality_error = validate_markdown_quality(raw_markdown, normalized_markdown)
        if quality_error:
            logger.warning(
                "resume-pdf-to-md AI output failed quality guard "
                "file=%s stage=%s provider=%s model=%s detail=%s",
                file_name,
                stage,
                provider,
                model,
                quality_error,
            )
            return (
                PdfToMarkdownAttempt(
                    provider=provider,
                    model=model,
                    stage=stage,
                    status="quality_guard_failed",
                    latency_ms=latency_ms,
                    error=quality_error,
                ),
                None,
                "quality_guard_failed",
            )

        return (
            PdfToMarkdownAttempt(
                provider=provider,
                model=model,
                stage=stage,
                status="success",
                latency_ms=latency_ms,
                error=None,
            ),
            normalized_markdown,
            None,
        )
    except AIClientError as exc:
        latency_ms = max(0, int((perf_counter() - request_started) * 1000))
        logger.warning(
            "resume-pdf-to-md AI normalization failed "
            "file=%s stage=%s provider=%s model=%s base_url=%s category=%s detail=%s",
            file_name,
            stage,
            ai_config.provider,
            ai_config.model,
            ai_config.base_url,
            exc.category,
            exc.detail,
        )
        return (
            PdfToMarkdownAttempt(
                provider=provider,
                model=model,
                stage=stage,
                status=_attempt_status_from_category(exc.category),
                latency_ms=latency_ms,
                error=exc.detail,
            ),
            None,
            exc.category,
        )
    except Exception:
        latency_ms = max(0, int((perf_counter() - request_started) * 1000))
        logger.exception(
            "resume-pdf-to-md AI normalization failed unexpectedly "
            "file=%s stage=%s provider=%s model=%s base_url=%s",
            file_name,
            stage,
            ai_config.provider,
            ai_config.model,
            ai_config.base_url,
        )
        return (
            PdfToMarkdownAttempt(
                provider=provider,
                model=model,
                stage=stage,
                status="http_error",
                latency_ms=latency_ms,
                error="AI provider error",
            ),
            None,
            "provider_error",
        )


async def pdf_to_markdown(
    pdf_bytes: bytes,
    file_name: str,
    *,
    ai_configs: list[AIProviderConfig] | None,
    retry_count_override: int = 0,
    total_timeout_budget_seconds: float | None = None,
) -> PdfToMarkdownResult:
    raw_markdown = extract_raw_markdown_from_pdf(pdf_bytes, file_name)
    ai_config_chain = list(ai_configs or [])
    primary_config = ai_config_chain[0] if ai_config_chain else None
    secondary_config = ai_config_chain[1] if len(ai_config_chain) > 1 else None
    primary_provider, primary_model = _provider_parts(primary_config)
    secondary_provider, secondary_model = _provider_parts(secondary_config)

    if not raw_markdown:
        return PdfToMarkdownResult(
            markdown="",
            raw_markdown="",
            cleaned_markdown="",
            ai_used=False,
            ai_provider="",
            ai_model="",
            ai_error="PDF 原始 Markdown 提取失败或为空",
            fallback_used=False,
            prompt_version=PROMPT_VERSION,
            ai_latency_ms=None,
            ai_path="rules",
            ai_attempts=[],
            ai_chain_latency_ms=None,
            degraded_used=True,
            configured_primary_provider=primary_provider,
            configured_primary_model=primary_model,
            configured_secondary_provider=secondary_provider,
            configured_secondary_model=secondary_model,
            last_attempt_status="",
            ai_error_category="parse_failure",
        )

    attempts: list[PdfToMarkdownAttempt] = []
    last_error: str | None = None
    last_error_category: str | None = None
    chain_started = perf_counter()

    primary_attempt, primary_markdown, primary_error_category = await _run_ai_attempt(
        stage="primary",
        file_name=file_name,
        raw_markdown=raw_markdown,
        ai_config=primary_config,
        retry_count_override=retry_count_override,
        total_timeout_budget_seconds=total_timeout_budget_seconds,
    )
    attempts.append(primary_attempt)
    if primary_attempt.status == "success" and primary_markdown is not None:
        if secondary_config is not None:
            attempts.append(
                _build_skipped_attempt(
                    stage="secondary",
                    config=secondary_config,
                    error="Primary provider succeeded",
                )
            )
        return PdfToMarkdownResult(
            markdown=primary_markdown,
            raw_markdown=raw_markdown,
            cleaned_markdown=primary_markdown,
            ai_used=True,
            ai_provider=primary_attempt.provider,
            ai_model=primary_attempt.model,
            ai_error=None,
            fallback_used=False,
            prompt_version=PROMPT_VERSION,
            ai_latency_ms=primary_attempt.latency_ms,
            ai_path="primary",
            ai_attempts=attempts,
            ai_chain_latency_ms=max(0, int((perf_counter() - chain_started) * 1000)),
            degraded_used=False,
            configured_primary_provider=primary_provider,
            configured_primary_model=primary_model,
            configured_secondary_provider=secondary_provider,
            configured_secondary_model=secondary_model,
            last_attempt_status=primary_attempt.status,
            ai_error_category=None,
        )

    last_error = primary_attempt.error
    last_error_category = primary_error_category

    if secondary_config is not None:
        secondary_attempt, secondary_markdown, secondary_error_category = await _run_ai_attempt(
            stage="secondary",
            file_name=file_name,
            raw_markdown=raw_markdown,
            ai_config=secondary_config,
            retry_count_override=retry_count_override,
        )
        attempts.append(secondary_attempt)
        if secondary_attempt.status == "success" and secondary_markdown is not None:
            return PdfToMarkdownResult(
                markdown=secondary_markdown,
                raw_markdown=raw_markdown,
                cleaned_markdown=secondary_markdown,
                ai_used=True,
                ai_provider=secondary_attempt.provider,
                ai_model=secondary_attempt.model,
                ai_error=None,
                fallback_used=False,
                prompt_version=PROMPT_VERSION,
                ai_latency_ms=secondary_attempt.latency_ms,
                ai_path="secondary",
                ai_attempts=attempts,
                ai_chain_latency_ms=max(0, int((perf_counter() - chain_started) * 1000)),
                degraded_used=True,
                configured_primary_provider=primary_provider,
                configured_primary_model=primary_model,
                configured_secondary_provider=secondary_provider,
                configured_secondary_model=secondary_model,
                last_attempt_status=secondary_attempt.status,
                ai_error_category=None,
            )
        if secondary_attempt.status != "skipped":
            last_error = secondary_attempt.error or last_error
            last_error_category = secondary_error_category or last_error_category

    final_latency_ms = next(
        (
            getattr(attempt, "latency_ms", None)
            for attempt in reversed(attempts)
            if getattr(attempt, "latency_ms", None) is not None
        ),
        None,
    )

    return PdfToMarkdownResult(
        markdown=raw_markdown,
        raw_markdown=raw_markdown,
        cleaned_markdown=raw_markdown,
        ai_used=False,
        ai_provider="",
        ai_model="",
        ai_error=last_error or "AI normalization failed, used raw Markdown",
        fallback_used=True,
        prompt_version=PROMPT_VERSION,
        ai_latency_ms=final_latency_ms,
        ai_path="rules",
        ai_attempts=attempts,
        ai_chain_latency_ms=max(0, int((perf_counter() - chain_started) * 1000)),
        degraded_used=True,
        configured_primary_provider=primary_provider,
        configured_primary_model=primary_model,
        configured_secondary_provider=secondary_provider,
        configured_secondary_model=secondary_model,
        last_attempt_status=str(getattr(attempts[-1], "status", "") or "") if attempts else "",
        ai_error_category=last_error_category or "provider_error",
    )


async def main():
    import sys

    if len(sys.argv) < 2:
        print("用法: python -m app.services.resume_pdf_to_md <pdf_file> [output_md_file]")
        return

    pdf_path = Path(sys.argv[1])
    output_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "output.md"
    )

    if not pdf_path.exists():
        print(f"文件不存在: {pdf_path}")
        return

    print(f"📄 处理文件: {pdf_path.name}")

    pdf_bytes = pdf_path.read_bytes()
    result = await pdf_to_markdown(pdf_bytes, pdf_path.name, ai_configs=[])

    if not result.markdown:
        print("❌ 处理失败: PDF 原始 Markdown 为空")
        return

    output_path.write_text(result.markdown, encoding="utf-8")
    print(f"✅ 已保存: {output_path}")
    print(f"\n{'='*60}\n")
    print(result.markdown)


if __name__ == "__main__":
    asyncio.run(main())
