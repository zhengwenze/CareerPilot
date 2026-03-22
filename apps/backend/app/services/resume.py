from __future__ import annotations

import asyncio
import importlib.util
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.db.session import get_session_factory
from app.models import Resume, ResumeParseJob, User
from app.schemas.resume import (
    ResumeDeleteResponse,
    ResumeDownloadUrlResponse,
    ResumeParseArtifactsData,
    ResumeParseJobResponse,
    ResumeResponse,
    ResumeStructuredData,
    ResumeStructuredUpdateRequest,
)
from app.services.match_support import mark_reports_stale_for_resume
from app.services.resume_parser import (
    build_initial_resume_parse_artifacts,
    build_resume_parse_artifacts,
    build_structured_resume,
)
from app.services.storage import ObjectStorage

SAFE_FILE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
SUPPORTED_RESUME_SUFFIXES = {".pdf"}
RESUME_PARSE_TIMEOUT_SECONDS = 180
AI_STATUS_PENDING = "pending"
AI_STATUS_APPLIED = "applied"
PARSE_PROGRESS_PREPARING = "排队完成，准备解析"
PARSE_PROGRESS_READING_FILE = "读取文件中"
PARSE_PROGRESS_PDF_TO_MARKDOWN = "PDF 转 Markdown 中"
PARSE_PROGRESS_STRUCTURING = "结构化整理中"

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
    spec.loader.exec_module(module)
    _RESUME_PDF_TO_MD_MODULE = module
    return module


async def convert_pdf_bytes_to_markdown(pdf_bytes: bytes, file_name: str) -> str:
    module = load_resume_pdf_to_md_module()
    pdf_to_markdown = getattr(module, "pdf_to_markdown", None)
    if pdf_to_markdown is None:
        raise RuntimeError("resume-pdf-to-md.py does not export pdf_to_markdown")

    markdown = await pdf_to_markdown(pdf_bytes, file_name)
    return str(markdown or "").strip()


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
        parse_artifacts_json=ResumeParseArtifactsData.model_validate(
            resume.parse_artifacts_json or {}
        ),
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
        ).model_dump(),
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
    del settings
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
    final_structured: ResumeStructuredData | None = None
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
            canonical_resume_md = await convert_pdf_bytes_to_markdown(
                file_bytes,
                resume.file_name,
            )
            if not canonical_resume_md:
                raise ApiException(
                    status_code=422,
                    code=ErrorCode.BAD_REQUEST,
                    message="PDF 转 Markdown 失败，未生成可用内容",
                )
            raw_text = canonical_resume_md

            await update_parse_job_progress(
                session_factory=session_maker,
                parse_job_id=parse_job_id,
                owner_user_id=owner_user_id,
                message=PARSE_PROGRESS_STRUCTURING,
            )
            final_structured = build_structured_resume(raw_text)
            final_structured.meta.source_type = extraction_source_type
            final_structured.meta.ai_correction_applied = True
            ai_status = AI_STATUS_APPLIED
            ai_message = "已通过 resume-pdf-to-md 生成 Markdown"
            log_renderer_snapshot(
                structured=final_structured,
                markdown=canonical_resume_md,
            )

        resume_parse_status = "success"
        resume_parse_error = None
        parse_job_status = "success"
        parse_job_error_message = None
    except TimeoutError:
        ai_status = None
        ai_message = None
        resume_parse_error = "Resume parse timed out"
        parse_job_error_message = "简历解析超时（E_PARSE_TIMEOUT）"
    except ApiException as exc:
        ai_status = None
        ai_message = None
        resume_parse_error = exc.message
        parse_job_error_message = f"{exc.message}（E_PARSE_API）"
    except Exception as exc:
        ai_status = None
        ai_message = None
        resume_parse_error = "Unexpected parse failure"
        parse_job_error_message = (
            f"{build_unexpected_parse_error_message(exc)}（E_PARSE_UNEXPECTED）"
        )

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

        if final_structured is not None and raw_text is not None:
            resume.raw_text = raw_text
            resume.structured_json = final_structured.model_dump()
        resume.parse_artifacts_json = build_resume_parse_artifacts(
            file_name=resume.file_name,
            raw_text=raw_text,
            structured=final_structured,
            canonical_resume_md=canonical_resume_md,
            ai_status=ai_status,
            parse_status=resume_parse_status,
            parse_error=resume_parse_error,
            source_type=extraction_source_type,
            ocr_used=extraction_ocr_used,
            ocr_engine=extraction_ocr_engine,
        ).model_dump()

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
    ).model_dump()
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
    resume.structured_json = payload.structured_json.model_dump()
    resume.latest_version += 1
    resume.updated_by = current_user.id

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
