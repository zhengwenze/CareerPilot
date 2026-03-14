from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.db.session import get_session_factory
from app.models import Resume, ResumeParseJob, User
from app.schemas.resume import (
    ResumeDownloadUrlResponse,
    ResumeParseJobResponse,
    ResumeResponse,
    ResumeStructuredData,
    ResumeStructuredUpdateRequest,
)
from app.services.resume_parser import build_structured_resume, extract_text_from_pdf_bytes
from app.services.storage import ObjectStorage

SAFE_FILE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_file_name(file_name: str) -> str:
    normalized = SAFE_FILE_NAME_PATTERN.sub("-", Path(file_name).name).strip("-")
    return normalized or f"resume-{uuid4().hex}.pdf"


def build_storage_object_key(*, user_id: UUID, resume_id: UUID, file_name: str) -> str:
    return f"resumes/{user_id}/{resume_id}/{file_name}"


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
) -> None:
    session_maker = session_factory or get_session_factory()
    async with session_maker() as session:
        resume = await session.get(Resume, resume_id)
        parse_job = await session.get(ResumeParseJob, parse_job_id)
        if resume is None or parse_job is None:
            return

        parse_job.status = "processing"
        parse_job.attempt_count += 1
        parse_job.error_message = None
        parse_job.started_at = datetime.now(UTC)
        parse_job.updated_by = resume.user_id
        resume.parse_status = "processing"
        resume.parse_error = None
        resume.updated_by = resume.user_id
        session.add(resume)
        session.add(parse_job)
        await session.commit()

        try:
            file_bytes = await storage.get_object_bytes(
                bucket_name=resume.storage_bucket,
                object_key=resume.storage_object_key,
            )
            raw_text = extract_text_from_pdf_bytes(file_bytes)
            structured = build_structured_resume(raw_text)

            resume.raw_text = raw_text
            resume.structured_json = structured.model_dump()
            resume.parse_status = "success"
            resume.parse_error = None
            resume.latest_version = max(resume.latest_version, 1)
            parse_job.status = "success"
            parse_job.error_message = None
        except ApiException as exc:
            resume.parse_status = "failed"
            resume.parse_error = exc.message
            parse_job.status = "failed"
            parse_job.error_message = exc.message
        except Exception as exc:
            resume.parse_status = "failed"
            resume.parse_error = "Unexpected parse failure"
            parse_job.status = "failed"
            parse_job.error_message = str(exc)
        finally:
            finished_at = datetime.now(UTC)
            resume.updated_by = resume.user_id
            parse_job.updated_by = resume.user_id
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
    resume = await get_resume_for_user(session, current_user=current_user, resume_id=resume_id)
    parse_job = await get_latest_parse_job(session, resume_id=resume.id)
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

    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    parse_job = await get_latest_parse_job(session, resume_id=resume.id)
    return serialize_resume(resume, parse_job=parse_job)
