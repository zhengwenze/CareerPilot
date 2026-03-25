import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.prompts.resume import get_resume_pdf_to_md_prompt
from app.services.ai_client import AIClientError, AIProviderConfig, request_text_completion

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PdfToMarkdownResult:
    markdown: str
    raw_markdown: str
    ai_applied: bool
    fallback_used: bool
    ai_error_category: str | None = None
    ai_error_message: str | None = None


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
- 必须完整保留所有有效联系方式和 URL
- 必须完整保留项目链接、仓库链接、个人主页链接
- 如果你发现项目标题附近存在 URL，请务必保留到最终输出中
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


async def pdf_to_markdown(
    pdf_bytes: bytes,
    file_name: str,
    *,
    ai_config: AIProviderConfig | None,
) -> PdfToMarkdownResult:
    raw_markdown = extract_raw_markdown_from_pdf(pdf_bytes, file_name)
    if not raw_markdown:
        return PdfToMarkdownResult(
            markdown="",
            raw_markdown="",
            ai_applied=False,
            fallback_used=False,
            ai_error_category="parse_failure",
            ai_error_message="PDF 原始 Markdown 提取失败或为空",
        )

    if ai_config is None or not (ai_config.api_key or "").strip():
        logger.warning(
            "resume-pdf-to-md AI normalization skipped due to missing API key "
            "file=%s provider=%s model=%s base_url=%s fallback_used=true",
            file_name,
            getattr(ai_config, "provider", ""),
            getattr(ai_config, "model", ""),
            getattr(ai_config, "base_url", ""),
        )
        return PdfToMarkdownResult(
            markdown=raw_markdown,
            raw_markdown=raw_markdown,
            ai_applied=False,
            fallback_used=True,
            ai_error_category="auth_error",
            ai_error_message="AI API Key 缺失，已回退原始 Markdown",
        )

    try:
        markdown = await request_text_completion(
            config=ai_config,
            instructions=get_resume_pdf_to_md_prompt(),
            payload={
                "raw_markdown": raw_markdown,
                "user_prompt": build_pdf_to_md_user_prompt(raw_markdown),
            },
            max_tokens=4000,
        )
        normalized_markdown = normalize_markdown(markdown)
        if not normalized_markdown:
            raise AIClientError(
                category="invalid_response_format",
                detail="AI response was empty after Markdown normalization",
            )
        return PdfToMarkdownResult(
            markdown=normalized_markdown,
            raw_markdown=raw_markdown,
            ai_applied=True,
            fallback_used=False,
        )
    except AIClientError as exc:
        logger.warning(
            "resume-pdf-to-md AI normalization failed "
            "file=%s provider=%s model=%s base_url=%s category=%s fallback_used=true detail=%s",
            file_name,
            ai_config.provider,
            ai_config.model,
            ai_config.base_url,
            exc.category,
            exc.detail,
        )
        return PdfToMarkdownResult(
            markdown=raw_markdown,
            raw_markdown=raw_markdown,
            ai_applied=False,
            fallback_used=True,
            ai_error_category=exc.category,
            ai_error_message=exc.detail,
        )
    except Exception:
        logger.exception(
            "resume-pdf-to-md AI normalization failed unexpectedly "
            "file=%s provider=%s model=%s base_url=%s fallback_used=true",
            file_name,
            ai_config.provider,
            ai_config.model,
            ai_config.base_url,
        )
        return PdfToMarkdownResult(
            markdown=raw_markdown,
            raw_markdown=raw_markdown,
            ai_applied=False,
            fallback_used=True,
            ai_error_category="provider_error",
            ai_error_message="AI provider error",
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
    result = await pdf_to_markdown(pdf_bytes, pdf_path.name, ai_config=None)

    if not result.markdown:
        print("❌ 处理失败: PDF 原始 Markdown 为空")
        return

    output_path.write_text(result.markdown, encoding="utf-8")
    print(f"✅ 已保存: {output_path}")
    print(f"\n{'='*60}\n")
    print(result.markdown)


if __name__ == "__main__":
    asyncio.run(main())
