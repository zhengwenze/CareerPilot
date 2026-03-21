from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.models import JobDescription, MatchReport, ResumeOptimizationSession, User
from app.schemas.job import JobCreateRequest, JobUpdateRequest
from app.schemas.match_report import MatchReportCreateRequest
from app.schemas.resume_optimization import ResumeOptimizationSessionCreateRequest
from app.schemas.tailored_resume import (
    TailoredResumeArtifactResponse,
    TailoredResumeGenerateRequest,
    TailoredResumeWorkflowResponse,
)
from app.services.job import (
    build_job_response,
    create_job,
    get_job_or_404,
    process_job_parse_job,
    update_job,
)
from app.services.match_report import (
    create_match_report,
    get_match_report_or_404,
    process_match_report,
)
from app.services.resume import get_resume_detail, get_resume_for_user
from app.services.resume_optimizer import (
    create_resume_optimization_session,
    generate_resume_optimization_suggestions,
    serialize_resume_optimization_session,
)


def _build_job_create_request(
    payload: TailoredResumeGenerateRequest,
) -> JobCreateRequest:
    return JobCreateRequest(
        title=payload.title,
        company=payload.company,
        job_city=payload.job_city,
        employment_type=payload.employment_type,
        source_name=payload.source_name,
        source_url=payload.source_url,
        priority=payload.priority,
        jd_text=payload.jd_text,
    )


def _build_job_update_request(
    payload: TailoredResumeGenerateRequest,
) -> JobUpdateRequest:
    return JobUpdateRequest(
        title=payload.title,
        company=payload.company,
        job_city=payload.job_city,
        employment_type=payload.employment_type,
        source_name=payload.source_name,
        source_url=payload.source_url,
        priority=payload.priority,
        jd_text=payload.jd_text,
    )


def _build_tailored_resume_artifact(
    *,
    session_payload,
    report: MatchReport,
) -> TailoredResumeArtifactResponse:
    return TailoredResumeArtifactResponse(
        session_id=session_payload.id,
        match_report_id=report.id,
        status=session_payload.status,
        fit_band=report.fit_band,
        overall_score=report.overall_score,
        optimized_resume_md=session_payload.optimized_resume_md,
        has_downloadable_markdown=session_payload.has_downloadable_markdown,
        downloadable_file_name=session_payload.downloadable_file_name,
        created_at=session_payload.created_at,
        updated_at=session_payload.updated_at,
    )


async def _build_workflow_response(
    session: AsyncSession,
    *,
    current_user: User,
    session_record: ResumeOptimizationSession,
    report: MatchReport,
) -> TailoredResumeWorkflowResponse:
    job = await get_job_or_404(session, current_user=current_user, job_id=session_record.jd_id)
    resume_payload = await get_resume_detail(
        session,
        current_user=current_user,
        resume_id=session_record.resume_id,
    )
    job_payload = await build_job_response(
        session,
        job=job,
        latest_match_report=report,
    )
    session_payload = serialize_resume_optimization_session(
        session_record,
        job=job,
        report=report,
    )
    return TailoredResumeWorkflowResponse(
        resume=resume_payload,
        target_job=job_payload,
        tailored_resume=_build_tailored_resume_artifact(
            session_payload=session_payload,
            report=report,
        ),
    )


def _ensure_resume_ready_for_tailoring(*, parse_status: str, has_structured_json: bool) -> None:
    if parse_status == "success" and has_structured_json:
        return
    raise ApiException(
        status_code=409,
        code=ErrorCode.CONFLICT,
        message="Resume must be parsed successfully before generating a tailored resume",
    )


def _ensure_job_ready_for_tailoring(job: JobDescription) -> None:
    if job.parse_status == "success" and job.structured_json:
        return
    message = job.parse_error or "Target job parsing did not finish successfully"
    raise ApiException(
        status_code=409,
        code=ErrorCode.CONFLICT,
        message=message,
    )


def _ensure_match_report_ready(report: MatchReport) -> None:
    if report.status == "success":
        return
    message = report.error_message or "Match report generation did not finish successfully"
    raise ApiException(
        status_code=409,
        code=ErrorCode.CONFLICT,
        message=message,
    )


async def list_tailored_resume_workflows(
    session: AsyncSession,
    *,
    current_user: User,
) -> list[TailoredResumeWorkflowResponse]:
    result = await session.execute(
        select(ResumeOptimizationSession)
        .where(ResumeOptimizationSession.user_id == current_user.id)
        .order_by(desc(ResumeOptimizationSession.created_at))
    )
    workflows: list[TailoredResumeWorkflowResponse] = []
    for session_record in result.scalars().all():
        report = await session.get(MatchReport, session_record.match_report_id)
        if report is None:
            continue
        workflows.append(
            await _build_workflow_response(
                session,
                current_user=current_user,
                session_record=session_record,
                report=report,
            )
        )
    return workflows


async def get_tailored_resume_workflow(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> TailoredResumeWorkflowResponse:
    result = await session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.id == session_id,
            ResumeOptimizationSession.user_id == current_user.id,
        )
    )
    session_record = result.scalar_one_or_none()
    if session_record is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Tailored resume workflow not found",
        )
    report = await session.get(MatchReport, session_record.match_report_id)
    if report is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Tailored resume match report not found",
        )
    return await _build_workflow_response(
        session,
        current_user=current_user,
        session_record=session_record,
        report=report,
    )


async def generate_tailored_resume_workflow(
    session: AsyncSession,
    *,
    current_user: User,
    payload: TailoredResumeGenerateRequest,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> TailoredResumeWorkflowResponse:
    resume = await get_resume_for_user(
        session,
        current_user=current_user,
        resume_id=payload.resume_id,
    )
    resume_id = resume.id
    _ensure_resume_ready_for_tailoring(
        parse_status=resume.parse_status,
        has_structured_json=bool(resume.structured_json),
    )

    if payload.job_id is None:
        job, parse_job = await create_job(
            session,
            current_user=current_user,
            payload=_build_job_create_request(payload),
        )
    else:
        job, parse_job = await update_job(
            session,
            current_user=current_user,
            job_id=payload.job_id,
            payload=_build_job_update_request(payload),
        )
    job_id = job.id

    if parse_job is not None:
        await process_job_parse_job(
            job_id=job_id,
            parse_job_id=parse_job.id,
            session_factory=session_factory,
        )

    session.expire_all()
    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    _ensure_job_ready_for_tailoring(job)

    report = await create_match_report(
        session,
        current_user=current_user,
        job_id=job.id,
        payload=MatchReportCreateRequest(
            resume_id=resume_id,
            force_refresh=payload.force_refresh,
        ),
    )
    report_id = report.id
    if report.status == "pending":
        await process_match_report(
            report_id=report_id,
            session_factory=session_factory,
            settings=settings,
        )
        session.expire_all()
        report = await get_match_report_or_404(
            session,
            current_user=current_user,
            report_id=report_id,
        )
    _ensure_match_report_ready(report)

    session_record, _resume, job, report = await create_resume_optimization_session(
        session,
        current_user=current_user,
        payload=ResumeOptimizationSessionCreateRequest(match_report_id=report.id),
    )
    session_id = session_record.id

    if session_record.status != "ready" or not session_record.optimized_resume_md.strip():
        await generate_resume_optimization_suggestions(
            session,
            current_user=current_user,
            session_id=session_id,
            settings=settings,
        )
        session.expire_all()
        refreshed = await get_tailored_resume_workflow(
            session,
            current_user=current_user,
            session_id=session_id,
        )
        return refreshed

    session.expire_all()
    return await get_tailored_resume_workflow(
        session,
        current_user=current_user,
        session_id=session_id,
    )
