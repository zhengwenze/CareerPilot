from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from uuid import UUID

from app.core.errors import ApiException, ErrorCode
from app.models import (
    JobDescription,
    JobReadinessEvent,
    MatchReport,
    Resume,
    ResumeOptimizationSession,
    User,
)
from app.schemas.resume import ResumeStructuredData
from app.schemas.resume_optimization import (
    ResumeOptimizationApplyResponse,
    ResumeOptimizationContext,
    ResumeOptimizationSectionDraft,
    ResumeOptimizationSessionCreateRequest,
    ResumeOptimizationSessionResponse,
    ResumeOptimizationTaskState,
    ResumeOptimizationSessionUpdateRequest,
)
from app.services.match_support import mark_reports_stale_for_resume


def _serialize_selected_tasks(raw_value: dict[str, Any]) -> list[ResumeOptimizationTaskState]:
    return [
        ResumeOptimizationTaskState.model_validate(item)
        for item in raw_value.get("tasks", [])
    ]


def _serialize_draft_sections(
    raw_value: dict[str, Any],
) -> dict[str, ResumeOptimizationSectionDraft]:
    sections: dict[str, ResumeOptimizationSectionDraft] = {}
    for key, value in raw_value.items():
        sections[key] = ResumeOptimizationSectionDraft.model_validate(value)
    return sections


def _build_optimizer_context(
    *,
    job: JobDescription,
    report: MatchReport,
) -> ResumeOptimizationContext:
    tailoring_plan = report.tailoring_plan_json or {}
    gap_json = report.gap_json or {}
    return ResumeOptimizationContext(
        job_id=job.id,
        match_report_id=report.id,
        job_title=job.title,
        company=job.company,
        fit_band=report.fit_band,
        stale_status=report.stale_status,
        target_summary=tailoring_plan.get("target_summary"),
        must_add_evidence=list(tailoring_plan.get("must_add_evidence", [])),
        gap_summary=[
            str(item.get("label"))
            for item in gap_json.get("gaps", [])
            if item.get("label")
        ][:5],
    )


def serialize_resume_optimization_session(
    session_record: ResumeOptimizationSession,
    *,
    job: JobDescription,
    report: MatchReport,
) -> ResumeOptimizationSessionResponse:
    return ResumeOptimizationSessionResponse(
        id=session_record.id,
        user_id=session_record.user_id,
        resume_id=session_record.resume_id,
        jd_id=session_record.jd_id,
        match_report_id=session_record.match_report_id,
        source_resume_version=session_record.source_resume_version,
        source_job_version=session_record.source_job_version,
        applied_resume_version=session_record.applied_resume_version,
        status=session_record.status,
        optimizer_context=_build_optimizer_context(job=job, report=report),
        tailoring_plan_snapshot=session_record.tailoring_plan_snapshot_json or {},
        draft_sections=_serialize_draft_sections(session_record.draft_sections_json or {}),
        selected_tasks=_serialize_selected_tasks(session_record.selected_tasks_json or {}),
        is_stale=report.stale_status == "stale",
        created_at=session_record.created_at,
        updated_at=session_record.updated_at,
    )


def _build_default_selected_tasks(report: MatchReport) -> list[ResumeOptimizationTaskState]:
    tasks = report.tailoring_plan_json.get("rewrite_tasks", [])
    result: list[ResumeOptimizationTaskState] = []
    for index, task in enumerate(tasks):
        target_section = str(task.get("target_section", "work_experience"))
        if target_section == "work_experience_or_projects":
            target_section = "work_experience"
        result.append(
            ResumeOptimizationTaskState(
                key=f"task-{index + 1}",
                title=str(task.get("title", f"改写任务 {index + 1}")),
                instruction=str(task.get("instruction", "")),
                target_section=target_section,
                priority=int(task.get("priority", index + 1)),
                selected=True,
            )
        )
    return result


def _newline_join(items: list[str]) -> str:
    return "\n".join(item for item in items if item.strip())


def _build_default_draft_sections(resume: ResumeStructuredData) -> dict[str, ResumeOptimizationSectionDraft]:
    return {
        "summary": ResumeOptimizationSectionDraft(
            key="summary",
            label="职业摘要",
            selected=True,
            original_text=resume.basic_info.summary,
            suggested_text=resume.basic_info.summary,
            mode="replace",
        ),
        "work_experience": ResumeOptimizationSectionDraft(
            key="work_experience",
            label="工作经历",
            selected=True,
            original_text=_newline_join(resume.work_experience),
            suggested_text="",
            mode="append",
        ),
        "projects": ResumeOptimizationSectionDraft(
            key="projects",
            label="项目经历",
            selected=True,
            original_text=_newline_join(resume.projects),
            suggested_text="",
            mode="append",
        ),
    }


def _build_rule_based_drafts(
    *,
    tailoring_plan_snapshot: dict[str, Any],
    selected_tasks: list[ResumeOptimizationTaskState],
    current_resume: ResumeStructuredData,
    current_sections: dict[str, ResumeOptimizationSectionDraft],
) -> dict[str, ResumeOptimizationSectionDraft]:
    next_sections = {
        key: ResumeOptimizationSectionDraft.model_validate(value.model_dump())
        for key, value in current_sections.items()
    }

    target_summary = str(tailoring_plan_snapshot.get("target_summary", "")).strip()
    evidence_items = list(tailoring_plan_snapshot.get("must_add_evidence", []))
    selected_by_section = {
        "summary": [item for item in selected_tasks if item.selected and item.target_section == "summary"],
        "work_experience": [
            item for item in selected_tasks if item.selected and item.target_section == "work_experience"
        ],
        "projects": [item for item in selected_tasks if item.selected and item.target_section == "projects"],
    }
    if not selected_by_section["projects"]:
        selected_by_section["projects"] = [
            item
            for item in selected_tasks
            if item.selected and item.target_section == "work_experience"
        ][:2]

    summary_parts: list[str] = []
    existing_summary = current_resume.basic_info.summary.strip()
    if target_summary:
        summary_parts.append(f"求职方向聚焦{target_summary}")
    if evidence_items:
        summary_parts.append(f"重点突出{', '.join(str(item) for item in evidence_items[:3])}等关键能力")
    summary_tail = "建议补充1至2个量化结果，写清职责范围、协作对象和业务影响。"
    if existing_summary:
        next_sections["summary"].suggested_text = (
            f"{existing_summary.rstrip('。')}。"
            f"{'，'.join(summary_parts)}，{summary_tail}"
            if summary_parts
            else f"{existing_summary.rstrip('。')}。{summary_tail}"
        )
    else:
        summary_body = "，".join(summary_parts) if summary_parts else "聚焦目标岗位要求"
        next_sections["summary"].suggested_text = (
            f"具备与目标岗位相关的项目推进和结果交付经验，{summary_body}，"
            "能够结合业务场景沉淀可复用的方法，并用量化结果证明价值。"
        )

    work_lines: list[str] = []
    for task in selected_by_section["work_experience"]:
        work_lines.append(
            f"在【业务场景】中负责{task.title}，通过【关键动作/分析方法】推动【核心指标】提升至【结果】。"
        )
    for item in evidence_items[:2]:
        work_lines.append(
            f"补充一条能证明{item}的经历，写清协作对象、你的判断动作，以及最终业务影响。"
        )
    next_sections["work_experience"].suggested_text = _newline_join(work_lines)

    project_lines: list[str] = []
    for task in selected_by_section["projects"]:
        project_lines.append(
            f"项目名称｜围绕{task.title}设计【方案/分析框架】，落地【关键动作】，最终带来【结果指标】。"
        )
    for item in evidence_items[2:4]:
        project_lines.append(
            f"如有与{item}相关项目，补充项目目标、关键取舍和量化结果，避免只写职责不写产出。"
        )
    next_sections["projects"].suggested_text = _newline_join(project_lines)

    return next_sections


async def _load_session_bundle(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> tuple[ResumeOptimizationSession, Resume, JobDescription, MatchReport]:
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
            message="Resume optimization session not found",
        )

    resume = await session.get(Resume, session_record.resume_id)
    job = await session.get(JobDescription, session_record.jd_id)
    report = await session.get(MatchReport, session_record.match_report_id)
    if resume is None or job is None or report is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Related optimizer context record not found",
        )
    return session_record, resume, job, report


async def _get_match_report_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    report_id: UUID,
) -> MatchReport:
    result = await session.execute(
        select(MatchReport).where(
            MatchReport.id == report_id,
            MatchReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Match report not found",
        )
    return report


def _ensure_optimizer_preconditions(*, report: MatchReport, resume: Resume) -> None:
    if report.status != "success":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Match report must be successful before optimization",
        )
    if report.stale_status != "fresh":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Match report is stale, please rerun matching first",
        )
    if resume.parse_status != "success" or not resume.structured_json:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Resume must be parsed successfully before optimization",
        )


async def create_resume_optimization_session(
    session: AsyncSession,
    *,
    current_user: User,
    payload: ResumeOptimizationSessionCreateRequest,
) -> tuple[ResumeOptimizationSession, Resume, JobDescription, MatchReport]:
    report = await _get_match_report_or_404(session, current_user=current_user, report_id=payload.match_report_id)
    resume = await session.get(Resume, report.resume_id)
    job = await session.get(JobDescription, report.jd_id)
    if resume is None or job is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Related optimizer context record not found",
        )
    _ensure_optimizer_preconditions(report=report, resume=resume)

    result = await session.execute(
        select(ResumeOptimizationSession)
        .where(
            ResumeOptimizationSession.user_id == current_user.id,
            ResumeOptimizationSession.match_report_id == report.id,
            ResumeOptimizationSession.source_resume_version == report.resume_version,
            ResumeOptimizationSession.source_job_version == report.job_version,
            ResumeOptimizationSession.status.in_(("draft", "ready")),
        )
        .order_by(desc(ResumeOptimizationSession.created_at))
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing, resume, job, report

    resume_snapshot = ResumeStructuredData.model_validate(resume.structured_json)
    selected_tasks = _build_default_selected_tasks(report)
    draft_sections = _build_default_draft_sections(resume_snapshot)
    session_record = ResumeOptimizationSession(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        source_resume_version=report.resume_version,
        source_job_version=report.job_version,
        applied_resume_version=None,
        status="draft",
        tailoring_plan_snapshot_json=report.tailoring_plan_json or {},
        draft_sections_json={key: value.model_dump() for key, value in draft_sections.items()},
        selected_tasks_json={"tasks": [item.model_dump() for item in selected_tasks]},
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return session_record, resume, job, report


async def get_resume_optimization_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> ResumeOptimizationSessionResponse:
    session_record, _resume, job, report = await _load_session_bundle(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    return serialize_resume_optimization_session(session_record, job=job, report=report)


async def generate_resume_optimization_suggestions(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> ResumeOptimizationSessionResponse:
    session_record, resume, job, report = await _load_session_bundle(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    resume_snapshot = ResumeStructuredData.model_validate(resume.structured_json or {})
    current_sections = _serialize_draft_sections(session_record.draft_sections_json or {})
    selected_tasks = _serialize_selected_tasks(session_record.selected_tasks_json or {})

    next_sections = _build_rule_based_drafts(
        tailoring_plan_snapshot=session_record.tailoring_plan_snapshot_json or {},
        selected_tasks=selected_tasks,
        current_resume=resume_snapshot,
        current_sections=current_sections,
    )

    session_record.draft_sections_json = {
        key: value.model_dump() for key, value in next_sections.items()
    }
    session_record.status = "ready"
    session_record.updated_by = current_user.id
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return serialize_resume_optimization_session(session_record, job=job, report=report)


async def update_resume_optimization_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    payload: ResumeOptimizationSessionUpdateRequest,
) -> ResumeOptimizationSessionResponse:
    session_record, _resume, job, report = await _load_session_bundle(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    session_record.draft_sections_json = {
        key: value.model_dump() for key, value in payload.draft_sections.items()
    }
    session_record.selected_tasks_json = {
        "tasks": [item.model_dump() for item in payload.selected_tasks]
    }
    session_record.status = "ready"
    session_record.updated_by = current_user.id
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return serialize_resume_optimization_session(session_record, job=job, report=report)


def _split_lines(value: str) -> list[str]:
    return [item.strip() for item in value.splitlines() if item.strip()]


async def apply_resume_optimization_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> ResumeOptimizationApplyResponse:
    session_record, resume, job, report = await _load_session_bundle(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    if session_record.status == "applied" and session_record.applied_resume_version is not None:
        return ResumeOptimizationApplyResponse(
            session_id=session_record.id,
            resume_id=resume.id,
            applied_resume_version=session_record.applied_resume_version,
        )

    sections = _serialize_draft_sections(session_record.draft_sections_json or {})
    resume_snapshot = ResumeStructuredData.model_validate(resume.structured_json or {})

    if "summary" in sections and sections["summary"].selected:
        if sections["summary"].suggested_text.strip():
            resume_snapshot.basic_info.summary = sections["summary"].suggested_text.strip()

    if "work_experience" in sections and sections["work_experience"].selected:
        suggestions = _split_lines(sections["work_experience"].suggested_text)
        for item in suggestions:
            if item not in resume_snapshot.work_experience:
                resume_snapshot.work_experience.append(item)

    if "projects" in sections and sections["projects"].selected:
        suggestions = _split_lines(sections["projects"].suggested_text)
        for item in suggestions:
            if item not in resume_snapshot.projects:
                resume_snapshot.projects.append(item)

    resume.structured_json = resume_snapshot.model_dump()
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
    session_record.status = "applied"
    session_record.applied_resume_version = resume.latest_version
    session_record.updated_by = current_user.id
    session.add(resume)
    session.add(session_record)
    session.add(
        JobReadinessEvent(
            user_id=current_user.id,
            job_id=job.id,
            resume_id=resume.id,
            match_report_id=report.id,
            status_from=job.status_stage,
            status_to="tailoring_applied",
            reason="Resume tailoring suggestions were applied to the structured resume",
            metadata_json={
                "session_id": str(session_record.id),
                "resume_version": resume.latest_version,
                "report_id": str(report.id),
            },
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    )
    await session.commit()
    await session.refresh(session_record)
    return ResumeOptimizationApplyResponse(
        session_id=session_record.id,
        resume_id=resume.id,
        applied_resume_version=resume.latest_version,
    )
