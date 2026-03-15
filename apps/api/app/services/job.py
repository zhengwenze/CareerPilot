from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException, ErrorCode
from app.models import JobDescription, MatchReport, User
from app.schemas.job import (
    JobCreateRequest,
    JobDeleteResponse,
    JobResponse,
    JobStructuredData,
    JobUpdateRequest,
)
from app.services.job_parser import build_structured_job


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message=f"{field_name} cannot be empty",
        )
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def serialize_job(job: JobDescription) -> JobResponse:
    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        title=job.title,
        company=job.company,
        job_city=job.job_city,
        employment_type=job.employment_type,
        source_name=job.source_name,
        source_url=job.source_url,
        jd_text=job.jd_text,
        parse_status=job.parse_status,
        parse_error=job.parse_error,
        structured_json=JobStructuredData.model_validate(job.structured_json)
        if job.structured_json
        else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _apply_job_parse(job: JobDescription) -> None:
    structured = build_structured_job(
        title=job.title,
        company=job.company,
        job_city=job.job_city,
        employment_type=job.employment_type,
        jd_text=job.jd_text,
    )
    job.structured_json = structured.model_dump()
    job.parse_status = "success"
    job.parse_error = None


async def get_job_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
) -> JobDescription:
    result = await session.execute(
        select(JobDescription).where(
            JobDescription.id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Job description not found",
        )
    return job


async def create_job(
    session: AsyncSession,
    *,
    current_user: User,
    payload: JobCreateRequest,
) -> JobDescription:
    job = JobDescription(
        user_id=current_user.id,
        title=_normalize_required_text(payload.title, field_name="title"),
        company=_normalize_optional_text(payload.company),
        job_city=_normalize_optional_text(payload.job_city),
        employment_type=_normalize_optional_text(payload.employment_type),
        source_name=_normalize_optional_text(payload.source_name),
        source_url=_normalize_optional_text(payload.source_url),
        jd_text=_normalize_required_text(payload.jd_text, field_name="jd_text"),
        parse_status="pending",
        parse_error=None,
        structured_json=None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    _apply_job_parse(job)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def list_jobs(
    session: AsyncSession,
    *,
    current_user: User,
    keyword: str | None = None,
    parse_status: str | None = None,
) -> list[JobDescription]:
    statement = select(JobDescription).where(JobDescription.user_id == current_user.id)

    normalized_keyword = _normalize_optional_text(keyword)
    if normalized_keyword is not None:
        pattern = f"%{normalized_keyword}%"
        statement = statement.where(
            or_(
                JobDescription.title.ilike(pattern),
                JobDescription.company.ilike(pattern),
                JobDescription.jd_text.ilike(pattern),
            )
        )

    normalized_parse_status = _normalize_optional_text(parse_status)
    if normalized_parse_status is not None:
        statement = statement.where(JobDescription.parse_status == normalized_parse_status)

    result = await session.execute(statement.order_by(desc(JobDescription.created_at)))
    return list(result.scalars().all())


async def update_job(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
    payload: JobUpdateRequest,
) -> JobDescription:
    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    updates = payload.model_dump(exclude_unset=True)

    should_reparse = job.structured_json is None or job.parse_status != "success"

    if "title" in updates:
        next_title = _normalize_required_text(updates["title"], field_name="title")
        if next_title != job.title:
            job.title = next_title
            should_reparse = True

    if "jd_text" in updates:
        next_jd_text = _normalize_required_text(updates["jd_text"], field_name="jd_text")
        if next_jd_text != job.jd_text:
            job.jd_text = next_jd_text
            should_reparse = True

    optional_fields = (
        "company",
        "job_city",
        "employment_type",
        "source_name",
        "source_url",
    )
    for field_name in optional_fields:
        if field_name in updates:
            next_value = _normalize_optional_text(updates[field_name])
            if getattr(job, field_name) != next_value:
                setattr(job, field_name, next_value)
                if field_name in {"company", "job_city", "employment_type"}:
                    should_reparse = True

    if should_reparse:
        job.parse_status = "pending"
        job.parse_error = None
        job.structured_json = None
        _apply_job_parse(job)

    job.updated_by = current_user.id
    if job.created_by is None:
        job.created_by = current_user.id

    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def parse_job(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
) -> JobDescription:
    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    job.parse_status = "pending"
    job.parse_error = None
    job.structured_json = None
    job.updated_by = current_user.id
    if job.created_by is None:
        job.created_by = current_user.id

    _apply_job_parse(job)

    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def delete_job(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
) -> JobDeleteResponse:
    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    report_exists = await session.execute(
        select(MatchReport.id).where(MatchReport.jd_id == job.id).limit(1)
    )
    if report_exists.scalar_one_or_none() is not None:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Job description already has match reports",
        )

    await session.delete(job)
    await session.commit()
    return JobDeleteResponse(message="Job description deleted successfully")
