from __future__ import annotations

import asyncio
import importlib.util
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.errors import ApiException, ErrorCode
from app.db.session import get_session_factory
from app.models import Resume, ResumeParseJob, User
from app.schemas.resume import (
    ResumeDeleteResponse,
    ResumeDownloadUrlResponse,
    ResumeParseJobResponse,
    ResumeResponse,
    ResumeStructuredData,
    ResumeStructuredUpdateRequest,
)
from app.services.match_support import mark_reports_stale_for_resume
from app.services.resume_markdown_parser import (
    normalize_resume_markdown_for_parser,
    parse_resume_markdown,
)
from app.services.storage import ObjectStorage

SAFE_FILE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
SUPPORTED_RESUME_SUFFIXES = {".pdf"}
RESUME_PARSE_TIMEOUT_SECONDS = 180
AI_STATUS_PENDING = "pending"
AI_STATUS_APPLIED = "applied"
AI_STATUS_FALLBACK = "fallback"
PARSE_PROGRESS_PREPARING = "排队完成，准备解析"
PARSE_PROGRESS_READING_FILE = "读取文件中"
PARSE_PROGRESS_PDF_TO_MARKDOWN = "PDF 转 Markdown 中"
logger = logging.getLogger(__name__)
_RESUME_PDF_TO_MD_MODULE: ModuleType | None = None


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def build_text_preview(value: str | None, *, limit: int = 160) -> str:
    if not value:
        return ""
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def build_initial_resume_parse_artifacts(*, file_name: str) -> dict[str, object]:
    return {
        "file_name": file_name,
        "raw_resume_md": "",
        "canonical_resume_md": "",
        "ai_used": False,
        "ai_provider": "",
        "ai_model": "",
        "ai_error": None,
        "fallback_used": False,
        "prompt_version": "",
        "ai_latency_ms": None,
        "ai_path": "",
        "ai_attempts": [],
        "ai_chain_latency_ms": None,
        "degraded_used": False,
        "configured_primary_provider": "",
        "configured_primary_model": "",
        "configured_secondary_provider": "",
        "configured_secondary_model": "",
        "last_attempt_status": "",
        "ai_error_category": None,
        "raw_text": "",
        "parse_status": "pending",
        "parse_error": None,
        "ai_status": "pending",
        "meta": {
            "source_type": "pdf",
            "parser_version": "demo-pdf-to-md",
            "ai_correction_applied": False,
            "ocr_used": False,
            "ocr_engine": "none",
        },
    }


def build_resume_parse_artifacts(
    *,
    file_name: str,
    raw_text: str | None,
    raw_resume_md: str | None,
    canonical_resume_md: str | None,
    ai_used: bool,
    ai_provider: str | None,
    ai_model: str | None,
    ai_error: str | None,
    fallback_used: bool,
    prompt_version: str | None,
    ai_latency_ms: int | None,
    ai_path: str | None,
    ai_attempts: list[object] | None,
    ai_chain_latency_ms: int | None,
    degraded_used: bool,
    configured_primary_provider: str | None,
    configured_primary_model: str | None,
    configured_secondary_provider: str | None,
    configured_secondary_model: str | None,
    last_attempt_status: str | None,
    ai_status: str | None,
    ai_correction_applied: bool,
    ai_error_category: str | None,
    ai_error_message: str | None,
    parse_status: str,
    parse_error: str | None,
    source_type: str,
    ocr_used: bool,
    ocr_engine: str,
) -> dict[str, object]:
    return {
        "file_name": file_name,
        "raw_resume_md": str(raw_resume_md or "").strip(),
        "canonical_resume_md": str(canonical_resume_md or "").strip(),
        "ai_used": ai_used,
        "ai_provider": str(ai_provider or "").strip(),
        "ai_model": str(ai_model or "").strip(),
        "ai_error": ai_error,
        "fallback_used": fallback_used,
        "prompt_version": str(prompt_version or "").strip(),
        "ai_latency_ms": ai_latency_ms,
        "ai_path": str(ai_path or "").strip(),
        "ai_attempts": [
            {
                "provider": str(getattr(attempt, "provider", "") or ""),
                "model": str(getattr(attempt, "model", "") or ""),
                "stage": str(getattr(attempt, "stage", "") or ""),
                "status": str(getattr(attempt, "status", "") or ""),
                "latency_ms": getattr(attempt, "latency_ms", None),
                "error": getattr(attempt, "error", None),
            }
            for attempt in (ai_attempts or [])
        ],
        "ai_chain_latency_ms": ai_chain_latency_ms,
        "degraded_used": degraded_used,
        "configured_primary_provider": str(configured_primary_provider or "").strip(),
        "configured_primary_model": str(configured_primary_model or "").strip(),
        "configured_secondary_provider": str(configured_secondary_provider or "").strip(),
        "configured_secondary_model": str(configured_secondary_model or "").strip(),
        "last_attempt_status": str(last_attempt_status or "").strip(),
        "ai_error_category": ai_error_category,
        "raw_text": str(raw_text or "").strip(),
        "parse_status": parse_status,
        "parse_error": parse_error,
        "ai_status": ai_status,
        "meta": {
            "source_type": source_type,
            "parser_version": "demo-pdf-to-md",
            "ai_correction_applied": ai_correction_applied,
            "ai_used": ai_used,
            "ai_provider": str(ai_provider or "").strip(),
            "ai_model": str(ai_model or "").strip(),
            "ai_status": ai_status,
            "ai_fallback_used": fallback_used,
            "fallback_used": fallback_used,
            "ai_error": ai_error,
            "ai_error_category": ai_error_category,
            "ai_error_message": ai_error_message,
            "prompt_version": str(prompt_version or "").strip(),
            "ai_latency_ms": ai_latency_ms,
            "ai_path": str(ai_path or "").strip(),
            "ai_chain_latency_ms": ai_chain_latency_ms,
            "degraded_used": degraded_used,
            "configured_primary_provider": str(configured_primary_provider or "").strip(),
            "configured_primary_model": str(configured_primary_model or "").strip(),
            "configured_secondary_provider": str(configured_secondary_provider or "").strip(),
            "configured_secondary_model": str(configured_secondary_model or "").strip(),
            "last_attempt_status": str(last_attempt_status or "").strip(),
            "ocr_used": ocr_used,
            "ocr_engine": ocr_engine,
        },
    }


def log_resume_pdf_to_markdown_result(
    *,
    resume_id: UUID | None,
    parse_job_id: UUID | None,
    pdf_to_md_result: object,
) -> None:
    attempts = list(getattr(pdf_to_md_result, "ai_attempts", []) or [])
    primary_latency_ms = next(
        (
            getattr(attempt, "latency_ms", None)
            for attempt in attempts
            if getattr(attempt, "stage", "") == "primary"
        ),
        None,
    )
    secondary_latency_ms = next(
        (
            getattr(attempt, "latency_ms", None)
            for attempt in attempts
            if getattr(attempt, "stage", "") == "secondary"
        ),
        None,
    )
    logger.info(
        "resume_pdf_to_markdown.completed resume_id=%s parse_job_id=%s ai_used=%s ai_error=%s "
        "markdown_length_before=%s markdown_length_after=%s fallback_used=%s prompt_version=%s ai_latency_ms=%s "
        "ai_path=%s degraded_used=%s ai_chain_latency_ms=%s ai_attempts_count=%s "
        "primary_latency_ms=%s secondary_latency_ms=%s configured_primary=%s/%s "
        "configured_secondary=%s/%s last_attempt_status=%s",
        resume_id,
        parse_job_id,
        getattr(pdf_to_md_result, "ai_used", False),
        getattr(pdf_to_md_result, "ai_error", None),
        len(getattr(pdf_to_md_result, "raw_markdown", "") or ""),
        len(getattr(pdf_to_md_result, "cleaned_markdown", "") or ""),
        getattr(pdf_to_md_result, "fallback_used", False),
        getattr(pdf_to_md_result, "prompt_version", ""),
        getattr(pdf_to_md_result, "ai_latency_ms", None),
        getattr(pdf_to_md_result, "ai_path", ""),
        getattr(pdf_to_md_result, "degraded_used", False),
        getattr(pdf_to_md_result, "ai_chain_latency_ms", None),
        len(attempts),
        primary_latency_ms,
        secondary_latency_ms,
        getattr(pdf_to_md_result, "configured_primary_provider", ""),
        getattr(pdf_to_md_result, "configured_primary_model", ""),
        getattr(pdf_to_md_result, "configured_secondary_provider", ""),
        getattr(pdf_to_md_result, "configured_secondary_model", ""),
        getattr(pdf_to_md_result, "last_attempt_status", ""),
    )


def log_renderer_snapshot(*, structured: ResumeStructuredData, markdown: str) -> None:
    logger.info(
        (
            "resume_markdown.rendered "
            "name=%s education_items=%s work_items=%s project_items=%s "
            "certifications=%s markdown_preview=%s"
        ),
        structured.basic_info.name,
        len(structured.education_items),
        len(structured.work_experience_items),
        len(structured.project_items),
        len(structured.certification_items),
        build_text_preview(markdown, limit=240),
    )


def load_resume_pdf_to_md_module() -> ModuleType:
    global _RESUME_PDF_TO_MD_MODULE
    if _RESUME_PDF_TO_MD_MODULE is not None:
        return _RESUME_PDF_TO_MD_MODULE

    module_path = Path(__file__).with_name("resume-pdf-to-md.py")
    spec = importlib.util.spec_from_file_location("app.services.resume_pdf_to_md_core", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load resume PDF to Markdown core: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _RESUME_PDF_TO_MD_MODULE = module
    return module


def build_resume_pdf_ai_configs(settings: Settings) -> list["AIProviderConfig"]:
    from app.services.ai_client import AIProviderConfig

    primary_config = AIProviderConfig(
        provider=(settings.resume_ai_provider or "codex2gpt").strip() or "codex2gpt",
        base_url=(settings.resume_ai_base_url or "").strip(),
        api_key=(settings.resume_ai_api_key or "").strip() or None,
        model=(settings.resume_ai_model or "gpt-5.4").strip(),
        timeout_seconds=settings.resume_pdf_ai_primary_timeout_seconds,
        connect_timeout_seconds=settings.resume_ai_connect_timeout_seconds,
        write_timeout_seconds=settings.resume_ai_write_timeout_seconds,
        read_timeout_seconds=settings.resume_ai_read_timeout_seconds,
        pool_timeout_seconds=settings.resume_ai_pool_timeout_seconds,
    )
    return [primary_config]


async def convert_pdf_bytes_to_markdown(
    pdf_bytes: bytes,
    file_name: str,
    *,
    settings: Settings,
):
    module = load_resume_pdf_to_md_module()
    pdf_to_markdown = getattr(module, "pdf_to_markdown", None)
    if pdf_to_markdown is None:
        raise RuntimeError("resume-pdf-to-md.py does not export pdf_to_markdown")

    return await pdf_to_markdown(
        pdf_bytes,
        file_name,
        ai_configs=build_resume_pdf_ai_configs(settings),
        retry_count_override=max(0, settings.resume_pdf_ai_retry_count),
        total_timeout_budget_seconds=settings.resume_pdf_ai_primary_timeout_seconds,
    )


def sanitize_file_name(file_name: str) -> str:
    original_name = Path(file_name).name
    suffix = Path(original_name).suffix.lower()
    stem = SAFE_FILE_NAME_PATTERN.sub("-", Path(original_name).stem).strip("-._")

    if suffix:
        return f"{stem or f'resume-{uuid4().hex}'}{suffix}"
    return stem or f"resume-{uuid4().hex}.pdf"


def set_parse_job_ai_result(
    parse_job: ResumeParseJob,
    *,
    status: str | None,
    message: str | None,
) -> None:
    parse_job.ai_status = status
    parse_job.ai_message = message


def build_unexpected_parse_error_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


def build_storage_object_key(*, user_id: UUID, resume_id: UUID, file_name: str) -> str:
    return f"resumes/{user_id}/{resume_id}/{file_name}"


def infer_resume_content_type(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    return {
        ".pdf": "application/pdf",
    }.get(suffix, "application/octet-stream")


async def update_parse_job_progress(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    parse_job_id: UUID,
    owner_user_id: UUID,
    message: str,
) -> None:
    try:
        async with session_factory() as session:
            parse_job = await session.get(ResumeParseJob, parse_job_id)
            if parse_job is None:
                logger.warning(
                    "Resume parse progress update skipped because parse job was missing: "
                    "parse_job_id=%s",
                    parse_job_id,
                )
                return
            set_parse_job_ai_result(
                parse_job,
                status=AI_STATUS_PENDING,
                message=message,
            )
            parse_job.updated_by = owner_user_id
            session.add(parse_job)
            await session.commit()
    except Exception:
        logger.warning(
            "Resume parse progress update failed: parse_job_id=%s message=%s",
            parse_job_id,
            message,
            exc_info=True,
        )


async def validate_resume_upload(
    file: UploadFile,
    *,
    settings: Settings,
) -> tuple[str, str, bytes]:
    if not file.filename:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Resume file name is required",
        )

    file_name = sanitize_file_name(file.filename)
    if Path(file_name).suffix.lower() not in SUPPORTED_RESUME_SUFFIXES:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Only text-based PDF resumes are supported",
        )

    max_file_size_bytes = settings.max_resume_file_size_mb * 1024 * 1024
    content = await file.read(max_file_size_bytes + 1)
    if not content:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Resume file cannot be empty",
        )
    if len(content) > max_file_size_bytes:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message=f"Resume file must be <= {settings.max_resume_file_size_mb} MB",
        )

    content_type = file.content_type or infer_resume_content_type(file_name)
    return file_name, content_type, content


def serialize_resume(
    resume: Resume,
    *,
    parse_job: ResumeParseJob | None,
    download_url: str | None = None,
) -> ResumeResponse:
    latest_parse_job = (
        ResumeParseJobResponse.model_validate(parse_job)
        if parse_job is not None
        else None
    )
    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        file_name=resume.file_name,
        file_url=resume.file_url,
        storage_bucket=resume.storage_bucket,
        storage_object_key=resume.storage_object_key,
        content_type=resume.content_type,
        file_size=resume.file_size,
        parse_status=resume.parse_status,
        parse_error=resume.parse_error,
        raw_text=resume.raw_text,
        structured_json=(
            ResumeStructuredData.model_validate(resume.structured_json)
            if resume.structured_json
            else None
        ),
        parse_artifacts_json=resume.parse_artifacts_json or {},
        latest_version=resume.latest_version,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        latest_parse_job=latest_parse_job,
        download_url=download_url,
    )


async def get_latest_parse_job(
    session: AsyncSession,
    *,
    resume_id: UUID,
) -> ResumeParseJob | None:
    result = await session.execute(
        select(ResumeParseJob)
        .where(ResumeParseJob.resume_id == resume_id)
        .order_by(desc(ResumeParseJob.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def upload_resume(
    session: AsyncSession,
    *,
    current_user: User,
    file: UploadFile,
    storage: ObjectStorage,
    settings: Settings,
) -> ResumeResponse:
    file_name, content_type, content = await validate_resume_upload(
        file, settings=settings
    )

    resume_id = uuid4()
    object_key = build_storage_object_key(
        user_id=current_user.id,
        resume_id=resume_id,
        file_name=file_name,
    )
    bucket_name = settings.storage_bucket_name
    stored_object = await storage.upload_bytes(
        bucket_name=bucket_name,
        object_key=object_key,
        data=content,
        content_type=content_type,
    )

    resume = Resume(
        id=resume_id,
        user_id=current_user.id,
        file_name=file_name,
        file_url=f"minio://{stored_object.bucket_name}/{stored_object.object_key}",
        storage_bucket=stored_object.bucket_name,
        storage_object_key=stored_object.object_key,
        content_type=content_type,
        file_size=len(content),
        parse_status="pending",
        parse_artifacts_json=build_initial_resume_parse_artifacts(
            file_name=file_name
        ),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    parse_job = ResumeParseJob(
        resume_id=resume.id,
        status="pending",
        attempt_count=0,
        created_by=current_user.id,
        updated_by=current_user.id,
    )

    try:
        session.add(resume)
        session.add(parse_job)
        await session.commit()
    except Exception:
        await session.rollback()
        await storage.delete_object(
            bucket_name=stored_object.bucket_name,
            object_key=stored_object.object_key,
        )
        raise

    await session.refresh(resume)
    await session.refresh(parse_job)
    return serialize_resume(resume, parse_job=parse_job)


async def process_resume_parse_job(
    *,
    resume_id: UUID,
    parse_job_id: UUID,
    storage: ObjectStorage,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    settings: Settings | None = None,
) -> None:
    config = settings or get_settings()
    session_maker = session_factory or get_session_factory()
    async with session_maker() as session:
        resume = await session.get(Resume, resume_id)
        parse_job = await session.get(ResumeParseJob, parse_job_id)
        if resume is None or parse_job is None:
            return

        parse_job.status = "processing"
        parse_job.attempt_count += 1
        set_parse_job_ai_result(
            parse_job,
            status=AI_STATUS_PENDING,
            message=PARSE_PROGRESS_PREPARING,
        )
        parse_job.error_message = None
        parse_job.started_at = utc_now_naive()
        parse_job.updated_by = resume.user_id
        resume.parse_status = "processing"
        resume.parse_error = None
        resume.updated_by = resume.user_id
        session.add(resume)
        session.add(parse_job)
        await session.commit()

        storage_bucket = resume.storage_bucket
        storage_object_key = resume.storage_object_key
        owner_user_id = resume.user_id

    raw_text: str | None = None
    raw_resume_md: str | None = None
    canonical_resume_md: str | None = None
    extraction_source_type = "pdf_to_md"
    extraction_ocr_used = False
    extraction_ocr_engine = "none"
    resume_parse_status = "failed"
    resume_parse_error: str | None = "Unexpected parse failure"
    parse_job_status = "failed"
    parse_job_error_message: str | None = "Unexpected parse failure"
    ai_status: str | None = None
    ai_message: str | None = None
    ai_used = False
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_error: str | None = None
    fallback_used = False
    prompt_version: str | None = None
    ai_latency_ms: int | None = None
    ai_path: str | None = None
    ai_attempts: list[object] = []
    ai_chain_latency_ms: int | None = None
    degraded_used = False
    configured_primary_provider: str | None = None
    configured_primary_model: str | None = None
    configured_secondary_provider: str | None = None
    configured_secondary_model: str | None = None
    last_attempt_status: str | None = None
    ai_error_category: str | None = None
    ai_error_message: str | None = None
    pdf_to_md_result = None

    try:
        async with asyncio.timeout(RESUME_PARSE_TIMEOUT_SECONDS):
            await update_parse_job_progress(
                session_factory=session_maker,
                parse_job_id=parse_job_id,
                owner_user_id=owner_user_id,
                message=PARSE_PROGRESS_READING_FILE,
            )
            file_bytes = await storage.get_object_bytes(
                bucket_name=storage_bucket,
                object_key=storage_object_key,
            )

            await update_parse_job_progress(
                session_factory=session_maker,
                parse_job_id=parse_job_id,
                owner_user_id=owner_user_id,
                message=PARSE_PROGRESS_PDF_TO_MARKDOWN,
            )
            pdf_to_md_result = await convert_pdf_bytes_to_markdown(
                file_bytes,
                resume.file_name,
                settings=config,
            )
            raw_resume_md = pdf_to_md_result.raw_markdown
            canonical_resume_md = pdf_to_md_result.cleaned_markdown
            raw_text = raw_resume_md or canonical_resume_md
            ai_used = pdf_to_md_result.ai_used
            ai_provider = pdf_to_md_result.ai_provider
            ai_model = pdf_to_md_result.ai_model
            ai_error = pdf_to_md_result.ai_error
            fallback_used = pdf_to_md_result.fallback_used
            prompt_version = pdf_to_md_result.prompt_version
            ai_latency_ms = pdf_to_md_result.ai_latency_ms
            ai_path = pdf_to_md_result.ai_path
            ai_attempts = list(pdf_to_md_result.ai_attempts or [])
            ai_chain_latency_ms = pdf_to_md_result.ai_chain_latency_ms
            degraded_used = pdf_to_md_result.degraded_used
            configured_primary_provider = pdf_to_md_result.configured_primary_provider
            configured_primary_model = pdf_to_md_result.configured_primary_model
            configured_secondary_provider = pdf_to_md_result.configured_secondary_provider
            configured_secondary_model = pdf_to_md_result.configured_secondary_model
            last_attempt_status = pdf_to_md_result.last_attempt_status
            ai_error_category = pdf_to_md_result.ai_error_category
            ai_error_message = pdf_to_md_result.ai_error_message
            if not canonical_resume_md:
                raise ApiException(
                    status_code=422,
                    code=ErrorCode.BAD_REQUEST,
                    message="PDF 转 Markdown 失败，未生成可用内容",
                )
            if pdf_to_md_result.ai_used:
                ai_status = AI_STATUS_APPLIED
                if ai_error_category == "quality_guard_failed":
                    ai_message = "已通过 AI 整理生成最终 Markdown（质量守卫仅记录告警，不再阻断）"
                else:
                    ai_message = (
                        "主模型失败，已降级次模型整理生成最终 Markdown"
                        if pdf_to_md_result.ai_path == "secondary"
                        else "已通过 AI 整理生成最终 Markdown"
                    )
            elif pdf_to_md_result.fallback_used:
                ai_status = AI_STATUS_FALLBACK
                ai_message = (
                    "AI 整理失败，已回退原始 Markdown"
                    if ai_error_category or ai_error_message
                    else "未应用 AI 整理，已使用原始 Markdown"
                )
            else:
                ai_status = None
                ai_message = None

        resume_parse_status = "success"
        resume_parse_error = None
        parse_job_status = "success"
        parse_job_error_message = None
    except TimeoutError:
        ai_status = None
        ai_message = None
        ai_error = "Resume parse timed out"
        resume_parse_error = "Resume parse timed out"
        parse_job_error_message = "简历解析超时（E_PARSE_TIMEOUT）"
        ai_error_category = "timeout"
        ai_error_message = resume_parse_error
    except ApiException as exc:
        ai_status = None
        ai_message = None
        ai_error = exc.message
        resume_parse_error = exc.message
        parse_job_error_message = f"{exc.message}（E_PARSE_API）"
        ai_error_category = "parse_failure"
        ai_error_message = exc.message
    except Exception as exc:
        ai_status = None
        ai_message = None
        ai_error = build_unexpected_parse_error_message(exc)
        resume_parse_error = "Unexpected parse failure"
        parse_job_error_message = (
            f"{build_unexpected_parse_error_message(exc)}（E_PARSE_UNEXPECTED）"
        )
        ai_error_category = "provider_error"
        ai_error_message = build_unexpected_parse_error_message(exc)

    async with session_maker() as session:
        resume = await session.get(Resume, resume_id)
        parse_job = await session.get(ResumeParseJob, parse_job_id)
        if resume is None or parse_job is None:
            logger.warning(
                "Resume parse finalization skipped because records were missing: "
                "resume_id=%s parse_job_id=%s",
                resume_id,
                parse_job_id,
            )
            return

        existing_artifacts = resume.parse_artifacts_json or {}
        existing_canonical_md = str(
            existing_artifacts.get("canonical_resume_md") or ""
        ).strip()
        existing_raw_text = str(resume.raw_text or "").strip()
        preserve_user_saved_markdown = (
            resume.parse_status == "success"
            and resume.latest_version > 1
            and bool(existing_canonical_md)
            and bool(existing_raw_text)
        )

        if not preserve_user_saved_markdown:
            if raw_text is not None:
                resume.raw_text = raw_text
            resume.parse_artifacts_json = build_resume_parse_artifacts(
                file_name=resume.file_name,
                raw_text=raw_text,
                raw_resume_md=raw_resume_md,
                canonical_resume_md=canonical_resume_md,
                ai_used=ai_used,
                ai_provider=ai_provider,
                ai_model=ai_model,
                ai_error=ai_error,
                fallback_used=fallback_used,
                prompt_version=prompt_version,
                ai_latency_ms=ai_latency_ms,
                ai_path=ai_path,
                ai_attempts=ai_attempts,
                ai_chain_latency_ms=ai_chain_latency_ms,
                degraded_used=degraded_used,
                configured_primary_provider=configured_primary_provider,
                configured_primary_model=configured_primary_model,
                configured_secondary_provider=configured_secondary_provider,
                configured_secondary_model=configured_secondary_model,
                last_attempt_status=last_attempt_status,
                ai_status=ai_status,
                ai_correction_applied=ai_status == AI_STATUS_APPLIED,
                ai_error_category=ai_error_category,
                ai_error_message=ai_error_message,
                parse_status=resume_parse_status,
                parse_error=resume_parse_error,
                source_type=extraction_source_type,
                ocr_used=extraction_ocr_used,
                ocr_engine=extraction_ocr_engine,
            )

        resume.parse_status = resume_parse_status
        resume.parse_error = resume_parse_error
        if resume_parse_status == "success":
            resume.latest_version = max(resume.latest_version, 1)

        parse_job.status = parse_job_status
        parse_job.error_message = parse_job_error_message
        set_parse_job_ai_result(
            parse_job,
            status=ai_status,
            message=ai_message,
        )

        finished_at = utc_now_naive()
        resume.updated_by = owner_user_id
        parse_job.updated_by = owner_user_id
        parse_job.finished_at = finished_at
        session.add(resume)
        session.add(parse_job)
        await session.commit()

    if pdf_to_md_result is not None:
        log_resume_pdf_to_markdown_result(
            resume_id=resume_id,
            parse_job_id=parse_job_id,
            pdf_to_md_result=pdf_to_md_result,
        )


async def list_resumes(
    session: AsyncSession,
    *,
    current_user: User,
) -> list[ResumeResponse]:
    result = await session.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(desc(Resume.created_at))
    )
    resumes = list(result.scalars().all())

    items: list[ResumeResponse] = []
    for resume in resumes:
        parse_job = await get_latest_parse_job(session, resume_id=resume.id)
        items.append(serialize_resume(resume, parse_job=parse_job))
    return items


async def list_resume_parse_jobs(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
) -> list[ResumeParseJobResponse]:
    await get_resume_for_user(session, current_user=current_user, resume_id=resume_id)
    result = await session.execute(
        select(ResumeParseJob)
        .join(Resume, Resume.id == ResumeParseJob.resume_id)
        .where(
            ResumeParseJob.resume_id == resume_id,
            Resume.user_id == current_user.id,
        )
        .order_by(desc(ResumeParseJob.created_at))
    )
    jobs = result.scalars().all()
    return [ResumeParseJobResponse.model_validate(job) for job in jobs]


async def get_resume_for_user(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
) -> Resume:
    result = await session.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Resume not found",
        )
    return resume


async def get_resume_detail(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
) -> ResumeResponse:
    resume = await get_resume_for_user(
        session, current_user=current_user, resume_id=resume_id
    )
    parse_job = await get_latest_parse_job(session, resume_id=resume.id)
    return serialize_resume(resume, parse_job=parse_job)


async def create_resume_parse_job(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
) -> tuple[Resume, ResumeParseJob]:
    resume = await get_resume_for_user(
        session, current_user=current_user, resume_id=resume_id
    )
    resume.parse_status = "pending"
    resume.parse_error = None
    resume.parse_artifacts_json = build_initial_resume_parse_artifacts(
        file_name=resume.file_name
    )
    resume.updated_by = current_user.id

    parse_job = ResumeParseJob(
        resume_id=resume.id,
        status="pending",
        attempt_count=0,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(resume)
    session.add(parse_job)
    await session.commit()
    await session.refresh(resume)
    await session.refresh(parse_job)
    return resume, parse_job


async def generate_resume_download_url(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
    storage: ObjectStorage,
    settings: Settings,
) -> ResumeDownloadUrlResponse:
    resume = await get_resume_for_user(
        session, current_user=current_user, resume_id=resume_id
    )
    download_url = await storage.get_download_url(
        bucket_name=resume.storage_bucket,
        object_key=resume.storage_object_key,
        expires_in_seconds=settings.storage_presigned_expire_seconds,
    )
    return ResumeDownloadUrlResponse(
        download_url=download_url,
        expires_in=settings.storage_presigned_expire_seconds,
    )


async def delete_resume(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
    storage: ObjectStorage,
) -> ResumeDeleteResponse:
    resume = await get_resume_for_user(
        session, current_user=current_user, resume_id=resume_id
    )

    await storage.delete_object(
        bucket_name=resume.storage_bucket,
        object_key=resume.storage_object_key,
    )

    await session.delete(resume)
    await session.commit()

    return ResumeDeleteResponse(message="Resume deleted successfully")


async def update_resume_structured_data(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
    payload: ResumeStructuredUpdateRequest,
) -> ResumeResponse:
    resume = await get_resume_for_user(
        session, current_user=current_user, resume_id=resume_id
    )
    normalized_markdown = str(payload.markdown or "").strip()
    try:
        structured = parse_resume_markdown(normalized_markdown)
    except ValueError as exc:
        fallback_markdown = normalize_resume_markdown_for_parser(normalized_markdown)
        if fallback_markdown and fallback_markdown != normalized_markdown:
            try:
                structured = parse_resume_markdown(fallback_markdown)
                normalized_markdown = fallback_markdown
            except ValueError:
                raise ApiException(
                    status_code=422,
                    code=ErrorCode.VALIDATION_ERROR,
                    message=str(exc),
                ) from exc
        else:
            raise ApiException(
                status_code=422,
                code=ErrorCode.VALIDATION_ERROR,
                message=str(exc),
            ) from exc

    resume.structured_json = structured.model_dump(mode="json")
    resume.raw_text = normalized_markdown
    artifacts = dict(resume.parse_artifacts_json or {})
    artifacts["canonical_resume_md"] = normalized_markdown
    meta = dict(artifacts.get("meta") or {})
    meta["source_type"] = "markdown"
    meta["parser_version"] = structured.meta.parser_version
    artifacts["meta"] = meta
    resume.parse_artifacts_json = artifacts
    resume.latest_version += 1
    resume.updated_by = current_user.id
    log_renderer_snapshot(structured=structured, markdown=normalized_markdown)

    if resume.parse_status != "success":
        resume.parse_status = "success"
        resume.parse_error = None

    await mark_reports_stale_for_resume(
        session,
        resume_id=resume.id,
        resume_version=resume.latest_version,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    parse_job = await get_latest_parse_job(session, resume_id=resume.id)
    return serialize_resume(resume, parse_job=parse_job)
