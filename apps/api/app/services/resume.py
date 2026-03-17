from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
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
from app.services.resume_ai import (
    ResumeAICorrectionRequest,
    build_resume_ai_correction_provider,
    merge_resume_ai_correction,
)
from app.services.resume_parser import build_structured_resume, extract_text_from_pdf_bytes
from app.services.storage import ObjectStorage

SAFE_FILE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
RESUME_PARSE_TIMEOUT_SECONDS = 120
AI_STATUS_PENDING = "pending"
AI_STATUS_APPLIED = "applied"
AI_STATUS_FALLBACK_RULE = "fallback_rule"
AI_STATUS_SKIPPED = "skipped"
logger = logging.getLogger(__name__)


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def build_text_preview(value: str | None, *, limit: int = 160) -> str:
    if not value:
        return ""
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


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


def build_storage_object_key(*, user_id: UUID, resume_id: UUID, file_name: str) -> str:
    return f"resumes/{user_id}/{resume_id}/{file_name}"


async def validate_resume_upload(
    file: UploadFile,
    *,
    settings: Settings,
) -> tuple[str, str, bytes]:
    logger.info(
        "Validating resume upload: file_name=%s content_type=%s",
        file.filename,
        file.content_type,
    )
    if not file.filename:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Resume file name is required",
        )

    file_name = sanitize_file_name(file.filename)
    if Path(file_name).suffix.lower() != ".pdf":
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Only PDF resumes are supported",
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

    content_type = file.content_type or "application/pdf"
    logger.info(
        "Validated resume upload: sanitized_file_name=%s size_bytes=%s content_type=%s",
        file_name,
        len(content),
        content_type,
    )
    return file_name, content_type, content


def serialize_resume(
    resume: Resume,
    *,
    parse_job: ResumeParseJob | None,
    download_url: str | None = None,
) -> ResumeResponse:
    latest_parse_job = (
        ResumeParseJobResponse.model_validate(parse_job) if parse_job is not None else None
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
        structured_json=ResumeStructuredData.model_validate(resume.structured_json)
        if resume.structured_json
        else None,
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
    file_name, content_type, content = await validate_resume_upload(file, settings=settings)
    logger.info(
        "Uploading resume to storage: user_id=%s file_name=%s size_bytes=%s",
        current_user.id,
        file_name,
        len(content),
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
    logger.info(
        "Uploaded resume to storage: user_id=%s resume_id=%s bucket=%s object_key=%s",
        current_user.id,
        resume_id,
        stored_object.bucket_name,
        stored_object.object_key,
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
    logger.info(
        (
            "Created resume and parse job records: resume_id=%s "
            "parse_job_id=%s parse_status=%s job_status=%s"
        ),
        resume.id,
        parse_job.id,
        resume.parse_status,
        parse_job.status,
    )
    return serialize_resume(resume, parse_job=parse_job)


async def process_resume_parse_job(
    *,
    resume_id: UUID,
    parse_job_id: UUID,
    storage: ObjectStorage,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    settings: Settings | None = None,
) -> None:
    logger.info(
        "Starting resume parse job: resume_id=%s parse_job_id=%s",
        resume_id,
        parse_job_id,
    )
    session_maker = session_factory or get_session_factory()
    config = settings or get_settings()
    async with session_maker() as session:
        resume = await session.get(Resume, resume_id)
        parse_job = await session.get(ResumeParseJob, parse_job_id)
        if resume is None or parse_job is None:
            logger.warning(
                "Resume parse job skipped because record was missing: resume_id=%s parse_job_id=%s",
                resume_id,
                parse_job_id,
            )
            return

        parse_job.status = "processing"
        parse_job.attempt_count += 1
        set_parse_job_ai_result(
            parse_job,
            status=AI_STATUS_PENDING,
            message="AI 校准进行中",
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
        logger.info(
            "Marked resume parse job as processing: resume_id=%s parse_job_id=%s",
            resume_id,
            parse_job_id,
        )

        try:
            async with asyncio.timeout(RESUME_PARSE_TIMEOUT_SECONDS):
                logger.info(
                    "Reading resume bytes from storage: resume_id=%s bucket=%s object_key=%s",
                    resume_id,
                    resume.storage_bucket,
                    resume.storage_object_key,
                )
                file_bytes = await storage.get_object_bytes(
                    bucket_name=resume.storage_bucket,
                    object_key=resume.storage_object_key,
                )
                logger.info(
                    "Loaded resume bytes from storage: resume_id=%s size_bytes=%s",
                    resume_id,
                    len(file_bytes),
                )
                raw_text = extract_text_from_pdf_bytes(file_bytes)
                logger.info(
                    (
                        "Extracted raw resume text: resume_id=%s "
                        "raw_text_length=%s raw_text_preview=%s"
                    ),
                    resume_id,
                    len(raw_text),
                    build_text_preview(raw_text),
                )
                structured = build_structured_resume(raw_text)
                logger.info(
                    (
                        "Built structured resume data: resume_id=%s name=%s email=%s "
                        "education_count=%s work_count=%s project_count=%s "
                        "technical_skill_count=%s"
                    ),
                    resume_id,
                    structured.basic_info.name,
                    structured.basic_info.email,
                    len(structured.education),
                    len(structured.work_experience),
                    len(structured.projects),
                    len(structured.skills.technical),
                )
                final_structured = structured
                ai_provider = build_resume_ai_correction_provider(config)
                try:
                    ai_result = await ai_provider.correct(
                        ResumeAICorrectionRequest(
                            raw_text=raw_text,
                            rule_structured_json=structured.model_dump(),
                        )
                    )
                    if ai_result.status == "applied" and ai_result.structured_data is not None:
                        final_structured = merge_resume_ai_correction(
                            raw_text=raw_text,
                            rule_result=structured,
                            ai_result=ai_result.structured_data,
                        )
                        set_parse_job_ai_result(
                            parse_job,
                            status=AI_STATUS_APPLIED,
                            message="AI 校准成功",
                        )
                        logger.info(
                            (
                                "Applied resume AI correction: resume_id=%s provider=%s model=%s "
                                "confidence=%s corrections=%s"
                            ),
                            resume_id,
                            ai_result.provider,
                            ai_result.model,
                            ai_result.confidence,
                            len(ai_result.corrections),
                        )
                    else:
                        set_parse_job_ai_result(
                            parse_job,
                            status=AI_STATUS_SKIPPED,
                            message="AI 校准未启用",
                        )
                        logger.info(
                            "Skipped resume AI correction: resume_id=%s provider=%s status=%s",
                            resume_id,
                            ai_result.provider,
                            ai_result.status,
                        )
                except Exception as exc:
                    set_parse_job_ai_result(
                        parse_job,
                        status=AI_STATUS_FALLBACK_RULE,
                        message="AI 校准失败，已回退规则解析",
                    )
                    logger.warning(
                        "Resume AI correction fallback to rule result: resume_id=%s reason=%s",
                        resume_id,
                        str(exc),
                    )

            resume.raw_text = raw_text
            resume.structured_json = final_structured.model_dump()
            resume.parse_status = "success"
            resume.parse_error = None
            resume.latest_version = max(resume.latest_version, 1)
            parse_job.status = "success"
            parse_job.error_message = None
        except TimeoutError:
            logger.warning(
                "Resume parse timed out: resume_id=%s parse_job_id=%s timeout_seconds=%s",
                resume_id,
                parse_job_id,
                RESUME_PARSE_TIMEOUT_SECONDS,
            )
            set_parse_job_ai_result(parse_job, status=None, message=None)
            resume.parse_status = "failed"
            resume.parse_error = "Resume parse timed out"
            parse_job.status = "failed"
            parse_job.error_message = "Resume parse timed out"
        except ApiException as exc:
            logger.warning(
                (
                    "Resume parse failed with ApiException: resume_id=%s "
                    "parse_job_id=%s message=%s details=%s"
                ),
                resume_id,
                parse_job_id,
                exc.message,
                exc.details,
            )
            set_parse_job_ai_result(parse_job, status=None, message=None)
            resume.parse_status = "failed"
            resume.parse_error = exc.message
            parse_job.status = "failed"
            parse_job.error_message = exc.message
        except Exception as exc:
            logger.exception(
                "Resume parse failed with unexpected exception: resume_id=%s parse_job_id=%s",
                resume_id,
                parse_job_id,
            )
            set_parse_job_ai_result(parse_job, status=None, message=None)
            resume.parse_status = "failed"
            resume.parse_error = "Unexpected parse failure"
            parse_job.status = "failed"
            parse_job.error_message = str(exc)
        finally:
            finished_at = utc_now_naive()
            resume.updated_by = resume.user_id
            parse_job.updated_by = resume.user_id
            parse_job.finished_at = finished_at
            session.add(resume)
            session.add(parse_job)
            await session.commit()
            logger.info(
                (
                    "Finished resume parse job: resume_id=%s parse_job_id=%s "
                    "resume_status=%s job_status=%s"
                ),
                resume_id,
                parse_job_id,
                resume.parse_status,
                parse_job.status,
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
    logger.info(
        "Listed resumes: user_id=%s count=%s statuses=%s",
        current_user.id,
        len(items),
        [
            {
                "resume_id": str(item.id),
                "parse_status": item.parse_status,
                "latest_parse_job_status": item.latest_parse_job.status
                if item.latest_parse_job
                else None,
            }
            for item in items
        ],
    )
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
    logger.info(
        "Listed resume parse jobs: user_id=%s resume_id=%s count=%s statuses=%s",
        current_user.id,
        resume_id,
        len(jobs),
        [job.status for job in jobs],
    )
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
    resume = await get_resume_for_user(session, current_user=current_user, resume_id=resume_id)
    parse_job = await get_latest_parse_job(session, resume_id=resume.id)
    logger.info(
        (
            "Loaded resume detail: user_id=%s resume_id=%s parse_status=%s "
            "parse_error=%s has_raw_text=%s has_structured_json=%s "
            "latest_parse_job_status=%s"
        ),
        current_user.id,
        resume_id,
        resume.parse_status,
        resume.parse_error,
        bool(resume.raw_text),
        bool(resume.structured_json),
        parse_job.status if parse_job is not None else None,
    )
    return serialize_resume(resume, parse_job=parse_job)


async def create_resume_parse_job(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
) -> tuple[Resume, ResumeParseJob]:
    resume = await get_resume_for_user(session, current_user=current_user, resume_id=resume_id)
    resume.parse_status = "pending"
    resume.parse_error = None
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
    logger.info(
        "Created manual retry parse job: user_id=%s resume_id=%s parse_job_id=%s",
        current_user.id,
        resume_id,
        parse_job.id,
    )
    return resume, parse_job


async def generate_resume_download_url(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
    storage: ObjectStorage,
    settings: Settings,
) -> ResumeDownloadUrlResponse:
    resume = await get_resume_for_user(session, current_user=current_user, resume_id=resume_id)
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
    resume = await get_resume_for_user(session, current_user=current_user, resume_id=resume_id)

    await storage.delete_object(
        bucket_name=resume.storage_bucket,
        object_key=resume.storage_object_key,
    )

    await session.delete(resume)
    await session.commit()
    logger.info(
        "Deleted resume record and object: user_id=%s resume_id=%s object_key=%s",
        current_user.id,
        resume_id,
        resume.storage_object_key,
    )

    return ResumeDeleteResponse(message="Resume deleted successfully")


async def update_resume_structured_data(
    session: AsyncSession,
    *,
    current_user: User,
    resume_id: UUID,
    payload: ResumeStructuredUpdateRequest,
) -> ResumeResponse:
    resume = await get_resume_for_user(session, current_user=current_user, resume_id=resume_id)
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
    logger.info(
        (
            "Updated structured resume data: user_id=%s resume_id=%s "
            "version=%s parse_status=%s name=%s"
        ),
        current_user.id,
        resume_id,
        resume.latest_version,
        resume.parse_status,
        payload.structured_json.basic_info.name,
    )
    return serialize_resume(resume, parse_job=parse_job)
