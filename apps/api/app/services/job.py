from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ApiException, ErrorCode
from app.models import JobDescription, JobParseJob, JobReadinessEvent, MatchReport, User
from app.schemas.job import (
    JobCreateRequest,
    JobDeleteResponse,
    JobLatestMatchReportSummary,
    JobParseJobResponse,
    JobReadinessEventResponse,
    JobResponse,
    JobStructuredData,
    JobUpdateRequest,
)
from app.services.job_parser import build_structured_job
from app.services.match_support import mark_reports_stale_for_job

JOB_PARSE_TIMEOUT_SECONDS = 120


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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


def _normalize_priority(value: int | None) -> int:
    if value is None:
        return 3
    return max(1, min(int(value), 5))


def _calculate_parse_confidence(structured: JobStructuredData) -> Decimal:
    signal_count = (
        len(structured.must_have)
        + len(structured.nice_to_have)
        + len(structured.domain_context.keywords)
        + len(structured.responsibilities)
    )
    confidence = min(0.98, 0.45 + min(signal_count, 10) * 0.05)
    if structured.raw_summary:
        confidence += 0.03
    return Decimal(f"{min(confidence, 0.99):.2f}")


def _build_competency_graph(structured: JobStructuredData) -> dict[str, object]:
    return {
        "must_have": structured.must_have[:8],
        "nice_to_have": structured.nice_to_have[:8],
        "responsibility_clusters": [
            {"name": cluster.name, "items": cluster.items[:3]}
            for cluster in structured.responsibility_clusters[:4]
        ],
        "keywords": structured.domain_context.keywords[:8],
        "seniority_hint": structured.domain_context.seniority_hint,
    }


def _serialize_latest_match_report_summary(
    report: MatchReport | None,
) -> JobLatestMatchReportSummary | None:
    if report is None:
        return None
    return JobLatestMatchReportSummary(
        id=report.id,
        status=report.status,
        overall_score=report.overall_score,
        fit_band=report.fit_band,
        stale_status=report.stale_status,
        resume_id=report.resume_id,
        resume_version=report.resume_version,
        created_at=report.created_at,
    )


def serialize_job(
    job: JobDescription,
    *,
    latest_parse_job: JobParseJob | None = None,
    latest_match_report: MatchReport | None = None,
    recent_readiness_events: list[JobReadinessEvent] | None = None,
) -> JobResponse:
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
        latest_version=job.latest_version,
        priority=job.priority,
        status_stage=job.status_stage,
        recommended_resume_id=job.recommended_resume_id,
        latest_match_report_id=job.latest_match_report_id,
        parse_confidence=job.parse_confidence,
        competency_graph_json=job.competency_graph_json or {},
        parse_status=job.parse_status,
        parse_error=job.parse_error,
        structured_json=JobStructuredData.model_validate(job.structured_json)
        if job.structured_json
        else None,
        latest_parse_job=JobParseJobResponse.model_validate(latest_parse_job)
        if latest_parse_job is not None
        else None,
        latest_match_report=_serialize_latest_match_report_summary(latest_match_report),
        recent_readiness_events=[
            JobReadinessEventResponse.model_validate(item)
            for item in (recent_readiness_events or [])
        ],
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def get_latest_job_parse_job(
    session: AsyncSession,
    *,
    job_id: UUID,
) -> JobParseJob | None:
    result = await session.execute(
        select(JobParseJob)
        .where(JobParseJob.job_id == job_id)
        .order_by(desc(JobParseJob.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_match_report_for_job(
    session: AsyncSession,
    *,
    job_id: UUID,
) -> MatchReport | None:
    result = await session.execute(
        select(MatchReport)
        .where(MatchReport.jd_id == job_id)
        .order_by(desc(MatchReport.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_recent_readiness_events(
    session: AsyncSession,
    *,
    job_id: UUID,
    limit: int = 5,
) -> list[JobReadinessEvent]:
    result = await session.execute(
        select(JobReadinessEvent)
        .where(JobReadinessEvent.job_id == job_id)
        .order_by(desc(JobReadinessEvent.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def _record_readiness_event(
    session: AsyncSession,
    *,
    job: JobDescription,
    current_user: User | None,
    status_from: str | None,
    status_to: str,
    reason: str,
    resume_id: UUID | None = None,
    match_report_id: UUID | None = None,
    metadata_json: dict | None = None,
) -> None:
    event = JobReadinessEvent(
        user_id=job.user_id,
        job_id=job.id,
        resume_id=resume_id,
        match_report_id=match_report_id,
        status_from=status_from,
        status_to=status_to,
        reason=reason,
        metadata_json=metadata_json or {},
        created_by=current_user.id if current_user is not None else job.user_id,
        updated_by=current_user.id if current_user is not None else job.user_id,
    )
    session.add(event)


def _derive_status_stage(
    job: JobDescription,
    *,
    latest_match_report: MatchReport | None = None,
) -> str:
    if job.parse_status != "success" or not job.structured_json:
        return "draft"
    if latest_match_report is None:
        return "analyzed"
    if latest_match_report.status != "success":
        return "matched"
    if latest_match_report.stale_status == "stale":
        return "matched"
    if latest_match_report.fit_band in {"excellent", "strong"}:
        return "interview_ready"
    return "tailoring_needed"


async def build_job_response(
    session: AsyncSession,
    *,
    job: JobDescription,
    latest_parse_job: JobParseJob | None = None,
    latest_match_report: MatchReport | None = None,
) -> JobResponse:
    next_parse_job = latest_parse_job or await get_latest_job_parse_job(session, job_id=job.id)
    next_match_report = latest_match_report or await get_latest_match_report_for_job(
        session,
        job_id=job.id,
    )
    recent_events = await list_recent_readiness_events(session, job_id=job.id)
    return serialize_job(
        job,
        latest_parse_job=next_parse_job,
        latest_match_report=next_match_report,
        recent_readiness_events=recent_events,
    )


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


async def get_job_response_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
) -> JobResponse:
    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    return await build_job_response(session, job=job)


async def create_job(
    session: AsyncSession,
    *,
    current_user: User,
    payload: JobCreateRequest,
) -> tuple[JobDescription, JobParseJob]:
    job = JobDescription(
        user_id=current_user.id,
        title=_normalize_required_text(payload.title, field_name="title"),
        company=_normalize_optional_text(payload.company),
        job_city=_normalize_optional_text(payload.job_city),
        employment_type=_normalize_optional_text(payload.employment_type),
        source_name=_normalize_optional_text(payload.source_name),
        source_url=_normalize_optional_text(payload.source_url),
        priority=_normalize_priority(payload.priority),
        jd_text=_normalize_required_text(payload.jd_text, field_name="jd_text"),
        latest_version=1,
        status_stage="draft",
        recommended_resume_id=None,
        latest_match_report_id=None,
        parse_confidence=None,
        competency_graph_json={},
        parse_status="pending",
        parse_error=None,
        structured_json=None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(job)
    await session.flush()

    parse_job = JobParseJob(
        job_id=job.id,
        status="pending",
        attempt_count=0,
        error_message=None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(parse_job)
    await _record_readiness_event(
        session,
        job=job,
        current_user=current_user,
        status_from=None,
        status_to="draft",
        reason="Target job created and queued for parsing",
        metadata_json={"priority": job.priority},
    )
    await session.commit()
    await session.refresh(job)
    await session.refresh(parse_job)
    return job, parse_job


async def list_jobs(
    session: AsyncSession,
    *,
    current_user: User,
    keyword: str | None = None,
    parse_status: str | None = None,
    status_stage: str | None = None,
    priority: int | None = None,
    stale: bool | None = None,
) -> list[JobResponse]:
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

    normalized_status_stage = _normalize_optional_text(status_stage)
    if normalized_status_stage is not None:
        statement = statement.where(JobDescription.status_stage == normalized_status_stage)

    if priority is not None:
        statement = statement.where(JobDescription.priority == priority)

    result = await session.execute(
        statement.order_by(JobDescription.priority.asc(), desc(JobDescription.created_at))
    )
    jobs = list(result.scalars().all())
    items: list[JobResponse] = []
    for job in jobs:
        latest_match_report = await get_latest_match_report_for_job(session, job_id=job.id)
        if stale is not None:
            is_stale = latest_match_report is not None and latest_match_report.stale_status == "stale"
            if is_stale != stale:
                continue
        items.append(
            await build_job_response(
                session,
                job=job,
                latest_match_report=latest_match_report,
            )
        )
    return items


async def create_job_parse_job(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
) -> tuple[JobDescription, JobParseJob]:
    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    previous_stage = job.status_stage
    job.parse_status = "pending"
    job.parse_error = None
    job.structured_json = None
    job.parse_confidence = None
    job.competency_graph_json = {}
    job.status_stage = "draft"
    job.updated_by = current_user.id

    parse_job = JobParseJob(
        job_id=job.id,
        status="pending",
        attempt_count=0,
        error_message=None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(job)
    session.add(parse_job)
    await _record_readiness_event(
        session,
        job=job,
        current_user=current_user,
        status_from=previous_stage,
        status_to=job.status_stage,
        reason="Job parsing re-queued",
    )
    await session.commit()
    await session.refresh(job)
    await session.refresh(parse_job)
    return job, parse_job


async def update_job(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
    payload: JobUpdateRequest,
) -> tuple[JobDescription, JobParseJob | None]:
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

    if "priority" in updates and updates["priority"] is not None:
        job.priority = _normalize_priority(updates["priority"])

    previous_stage = job.status_stage
    parse_job: JobParseJob | None = None
    if should_reparse:
        job.latest_version += 1
        job.parse_status = "pending"
        job.parse_error = None
        job.structured_json = None
        job.parse_confidence = None
        job.competency_graph_json = {}
        job.status_stage = "draft"
        parse_job = JobParseJob(
            job_id=job.id,
            status="pending",
            attempt_count=0,
            error_message=None,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        session.add(parse_job)

    job.updated_by = current_user.id
    if job.created_by is None:
        job.created_by = current_user.id

    session.add(job)
    if previous_stage != job.status_stage:
        await _record_readiness_event(
            session,
            job=job,
            current_user=current_user,
            status_from=previous_stage,
            status_to=job.status_stage,
            reason="Job updated and queued for re-parsing",
            metadata_json={"version": job.latest_version},
        )
    await session.commit()
    await session.refresh(job)
    if parse_job is not None:
        await session.refresh(parse_job)
    return job, parse_job


async def process_job_parse_job(
    *,
    job_id: UUID,
    parse_job_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        job = await session.get(JobDescription, job_id)
        parse_job = await session.get(JobParseJob, parse_job_id)
        if job is None or parse_job is None:
            return

        parse_job.status = "processing"
        parse_job.attempt_count += 1
        parse_job.error_message = None
        parse_job.started_at = utc_now_naive()
        parse_job.updated_by = job.user_id
        job.parse_status = "processing"
        job.parse_error = None
        job.updated_by = job.user_id
        session.add(job)
        session.add(parse_job)
        await session.commit()

    async with session_factory() as session:
        job = await session.get(JobDescription, job_id)
        parse_job = await session.get(JobParseJob, parse_job_id)
        if job is None or parse_job is None:
            return

        try:
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
            job.parse_confidence = _calculate_parse_confidence(structured)
            job.competency_graph_json = _build_competency_graph(structured)
            await mark_reports_stale_for_job(
                session,
                job_id=job.id,
                job_version=job.latest_version,
            )
            latest_report = await get_latest_match_report_for_job(session, job_id=job.id)
            previous_stage = job.status_stage
            job.status_stage = _derive_status_stage(job, latest_match_report=latest_report)
            parse_job.status = "success"
            parse_job.error_message = None
            await _record_readiness_event(
                session,
                job=job,
                current_user=None,
                status_from=previous_stage,
                status_to=job.status_stage,
                reason="Job parsed successfully",
                metadata_json={"version": job.latest_version},
            )
        except TimeoutError:
            job.parse_status = "failed"
            job.parse_error = "Job parse timed out"
            parse_job.status = "failed"
            parse_job.error_message = "Job parse timed out"
        except Exception as exc:
            job.parse_status = "failed"
            job.parse_error = str(exc)
            parse_job.status = "failed"
            parse_job.error_message = str(exc)
        finally:
            finished_at = utc_now_naive()
            job.updated_by = job.user_id
            parse_job.updated_by = job.user_id
            parse_job.finished_at = finished_at
            session.add(job)
            session.add(parse_job)
            await session.commit()


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
