import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from app.prompts.resume import get_resume_pdf_to_md_prompt
from app.services.ai_client import AIProviderConfig, request_text_completion

load_dotenv(Path(__file__).parent / ".env")

MODEL_API_KEY = os.getenv("MATCH_AI_API_KEY", "").strip()
if not MODEL_API_KEY:
    MODEL_API_KEY = os.getenv("MINIMAX_API_KEY", "").strip()
MODEL_BASE_URL = os.getenv(
    "MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"
).strip()
MODEL_NAME = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5").strip()


async def pdf_to_markdown(pdf_bytes: bytes, file_name: str) -> str:
    try:
        import pymupdf4llm
    except ImportError:
        return ""

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        raw_md = pymupdf4llm.to_markdown(tmp_path).strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not raw_md.strip():
        return ""

    user_prompt = f"""下面是从 PDF 简历中提取出来的原始 Markdown，请你整理成最终简历 Markdown。

请特别注意：
- 这是"高保真转换"任务，不是"润色改写"任务
- 必须完整保留所有有效联系方式和 URL
- 必须完整保留项目链接、仓库链接、个人主页链接
- 如果你发现项目标题附近存在 URL，请务必保留到最终输出中
- 优先保留信息，不要为了美观省略内容
- 如果原始 Markdown 已经较好，只做最小必要清洗

请直接输出最终 Markdown，不要输出解释。

---------------- RAW MARKDOWN BEGIN ----------------
{raw_md}
---------------- RAW MARKDOWN END ----------------
"""

    try:
        markdown = await request_text_completion(
            config=AIProviderConfig(
                provider="anthropic",
                base_url=MODEL_BASE_URL,
                api_key=MODEL_API_KEY,
                model=MODEL_NAME,
                timeout_seconds=60,
            ),
            instructions=get_resume_pdf_to_md_prompt(),
            payload={"raw_markdown": raw_md, "user_prompt": user_prompt},
            max_tokens=4000,
        )
        return markdown.strip()
    except Exception:
        return ""


async def main():
    import sys

    if len(sys.argv) < 2:
        print("用法: python -m app.services.resume_pdf_to_md <pdf_file> [output_md_file]")
        return

    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "output.md"

    if not pdf_path.exists():
        print(f"文件不存在: {pdf_path}")
        return

    print(f"📄 处理文件: {pdf_path.name}")

    pdf_bytes = pdf_path.read_bytes()
    markdown = await pdf_to_markdown(pdf_bytes, pdf_path.name)

    if not markdown:
        print("❌ 处理失败: AI 输出为空")
        return

    output_path.write_text(markdown, encoding="utf-8")
    print(f"✅ 已保存: {output_path}")
    print(f"\n{'='*60}\n")
    print(markdown)


if __name__ == "__main__":
    asyncio.run(main())
