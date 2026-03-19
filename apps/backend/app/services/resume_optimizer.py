from __future__ import annotations

import re
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

TEXT_TOKEN_PATTERN = re.compile(r"[a-z0-9+#./-]+|[\u4e00-\u9fff]+", re.IGNORECASE)
SECTION_TEXT_LABELS = ("原始证据：", "改写重点：", "建议草案：", "缺失证据清单：")


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
        result.append(
            ResumeOptimizationTaskState(
                key=f"task-{index + 1}",
                title=str(task.get("title", f"改写任务 {index + 1}")),
                instruction=str(task.get("instruction", "")),
                target_section=str(task.get("target_section", "work_experience_or_projects")),
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


def _normalize_line(value: str) -> str:
    return " ".join(value.split()).strip().lower()


def _dedupe_strings(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = _normalize_line(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item.strip())
    return result


def _flatten_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_flatten_string_values(item))
        return result
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_flatten_string_values(item))
        return result
    return []


def _tokenize_text(value: str) -> set[str]:
    tokens: set[str] = set()
    for chunk in TEXT_TOKEN_PATTERN.findall(value.lower()):
        token = chunk.strip()
        if not token:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            if len(token) <= 4:
                tokens.add(token)
                continue
            for size in (2, 3, 4):
                for index in range(0, len(token) - size + 1):
                    tokens.add(token[index : index + size])
            continue
        if len(token) >= 2:
            tokens.add(token)
    return tokens


def _build_task_query_terms(
    *,
    task: ResumeOptimizationTaskState,
    evidence_items: list[str],
    matched_jd_fields: dict[str, Any],
) -> list[str]:
    return _dedupe_strings(
        [
            task.title,
            task.instruction,
            *evidence_items,
            *_flatten_string_values(matched_jd_fields),
        ]
    )


def _score_section_item(item: str, query_terms: list[str]) -> int:
    item_text = item.strip()
    if not item_text:
        return 0
    item_tokens = _tokenize_text(item_text)
    if not item_tokens:
        return 0

    score = 0
    for term in query_terms:
        normalized_term = term.strip()
        if not normalized_term:
            continue
        term_tokens = _tokenize_text(normalized_term)
        if normalized_term.lower() in item_text.lower():
            score += 3
        overlap = item_tokens & term_tokens
        score += len(overlap)
    return score


def _pick_section_anchors(
    *,
    items: list[str],
    query_terms: list[str],
) -> list[str]:
    scored_items = [
        (item, _score_section_item(item, query_terms))
        for item in items
        if item.strip()
    ]
    scored_items = [item for item in scored_items if item[1] > 0]
    scored_items.sort(key=lambda pair: (-pair[1], pair[0].lower()))
    return [item for item, _score in scored_items[:2]]


def _resolve_target_section(
    *,
    task: ResumeOptimizationTaskState,
    current_resume: ResumeStructuredData,
    evidence_items: list[str],
    matched_jd_fields: dict[str, Any],
) -> str:
    if task.target_section in {"summary", "work_experience", "projects"}:
        return task.target_section

    query_terms = _build_task_query_terms(
        task=task,
        evidence_items=evidence_items,
        matched_jd_fields=matched_jd_fields,
    )
    work_anchors = _pick_section_anchors(
        items=current_resume.work_experience,
        query_terms=query_terms,
    )
    project_anchors = _pick_section_anchors(
        items=current_resume.projects,
        query_terms=query_terms,
    )
    if len(project_anchors) > len(work_anchors):
        return "projects"
    if len(work_anchors) > len(project_anchors):
        return "work_experience"

    work_score = max(
        (_score_section_item(item, query_terms) for item in current_resume.work_experience if item.strip()),
        default=0,
    )
    project_score = max(
        (_score_section_item(item, query_terms) for item in current_resume.projects if item.strip()),
        default=0,
    )
    if project_score > work_score:
        return "projects"
    if work_score > project_score:
        return "work_experience"

    combined_text = " ".join([task.title, task.instruction]).lower()
    if "项目" in combined_text:
        return "projects"
    return "work_experience"


def _build_summary_draft(
    *,
    current_resume: ResumeStructuredData,
    target_summary: str,
    evidence_items: list[str],
) -> str:
    summary_parts = _dedupe_strings(
        [
            current_resume.basic_info.summary.strip(),
            f"求职方向聚焦{target_summary}" if target_summary else "",
            (
                f"重点补强{'、'.join(evidence_items[:2])}等岗位证据"
                if evidence_items
                else ""
            ),
        ]
    )
    return "。".join(item.rstrip("。") for item in summary_parts if item).strip()


def _build_focus_points(
    *,
    task: ResumeOptimizationTaskState,
    evidence_items: list[str],
    gap_labels: list[str],
    target_summary: str,
) -> list[str]:
    return _dedupe_strings(
        [
            task.title,
            *evidence_items[:2],
            *gap_labels[:2],
            f"贴合{target_summary}" if target_summary else "",
        ]
    )


def _build_anchor_suggestion(
    *,
    anchor: str,
    focus_points: list[str],
    task: ResumeOptimizationTaskState,
) -> str:
    anchor_text = anchor.strip().rstrip("。；;，,")
    focus_text = "、".join(focus_points[:3])
    if focus_text:
        return f"{anchor_text}，重点突出{focus_text}，并补强{task.title}相关表达。"
    return f"{anchor_text}，可进一步补强{task.title}相关表达。"


def _build_missing_evidence_block(
    *,
    task: ResumeOptimizationTaskState,
    evidence_items: list[str],
    gap_labels: list[str],
) -> str:
    missing_items = _dedupe_strings(
        [
            task.title,
            *evidence_items[:2],
            *gap_labels[:2],
        ]
    )
    if not missing_items:
        missing_items = [task.title]
    missing_lines = "\n".join(f"- {item}" for item in missing_items[:3])
    return f"缺失证据清单：\n{missing_lines}"


def _build_section_draft(
    *,
    section_key: str,
    items: list[str],
    tasks: list[ResumeOptimizationTaskState],
    evidence_items: list[str],
    matched_jd_fields: dict[str, Any],
    gap_labels: list[str],
    target_summary: str,
) -> str:
    blocks: list[str] = []
    used_anchors: set[str] = set()
    for task in tasks:
        query_terms = _build_task_query_terms(
            task=task,
            evidence_items=evidence_items,
            matched_jd_fields=matched_jd_fields,
        )
        anchors = _pick_section_anchors(items=items, query_terms=query_terms)
        if not anchors:
            blocks.append(
                _build_missing_evidence_block(
                    task=task,
                    evidence_items=evidence_items,
                    gap_labels=gap_labels,
                )
            )
            continue

        focus_points = _build_focus_points(
            task=task,
            evidence_items=evidence_items,
            gap_labels=gap_labels,
            target_summary=target_summary,
        )
        for anchor in anchors:
            normalized_anchor = _normalize_line(anchor)
            if normalized_anchor in used_anchors:
                continue
            used_anchors.add(normalized_anchor)
            blocks.append(
                "\n".join(
                    [
                        f"原始证据：{anchor}",
                        f"改写重点：{'、'.join(focus_points[:3]) or task.title}",
                        f"建议草案：{_build_anchor_suggestion(anchor=anchor, focus_points=focus_points, task=task)}",
                    ]
                )
            )

    if not blocks and section_key == "projects" and not items:
        return "缺失证据清单：\n- 当前简历还没有项目经历，可先补充与目标岗位直接相关的项目事实。"
    return "\n\n".join(blocks)


def _build_rule_based_drafts(
    *,
    tailoring_plan_snapshot: dict[str, Any],
    evidence_map_json: dict[str, Any],
    gap_json: dict[str, Any],
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
    matched_jd_fields = evidence_map_json.get("matched_jd_fields", {})
    gap_labels = [
        str(item.get("label", "")).strip()
        for item in gap_json.get("gaps", [])
        if isinstance(item, dict) and str(item.get("label", "")).strip()
    ]

    selected_by_section = {"summary": [], "work_experience": [], "projects": []}
    for task in selected_tasks:
        if not task.selected:
            continue
        section_key = _resolve_target_section(
            task=task,
            current_resume=current_resume,
            evidence_items=evidence_items,
            matched_jd_fields=matched_jd_fields,
        )
        selected_by_section.setdefault(section_key, []).append(task)

    next_sections["summary"].suggested_text = _build_summary_draft(
        current_resume=current_resume,
        target_summary=target_summary,
        evidence_items=evidence_items,
    )
    next_sections["work_experience"].suggested_text = _build_section_draft(
        section_key="work_experience",
        items=current_resume.work_experience,
        tasks=selected_by_section["work_experience"],
        evidence_items=evidence_items,
        matched_jd_fields=matched_jd_fields,
        gap_labels=gap_labels,
        target_summary=target_summary,
    )
    next_sections["projects"].suggested_text = _build_section_draft(
        section_key="projects",
        items=current_resume.projects,
        tasks=selected_by_section["projects"],
        evidence_items=evidence_items,
        matched_jd_fields=matched_jd_fields,
        gap_labels=gap_labels,
        target_summary=target_summary,
    )

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
        evidence_map_json=report.evidence_map_json or {},
        gap_json=report.gap_json or {},
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


def _extract_apply_lines(value: str) -> list[str]:
    lines = _split_lines(value)
    suggestion_lines = [
        line.split("建议草案：", 1)[1].strip()
        for line in lines
        if line.startswith("建议草案：") and line.split("建议草案：", 1)[1].strip()
    ]
    if suggestion_lines:
        return _dedupe_strings(suggestion_lines)
    if any(
        line.startswith(label) or line.startswith("- ")
        for line in lines
        for label in SECTION_TEXT_LABELS
    ):
        return []
    return _dedupe_strings(lines)


def _apply_summary_mode(*, current_value: str, draft: ResumeOptimizationSectionDraft) -> str:
    suggested_text = draft.suggested_text.strip()
    if not suggested_text:
        return current_value
    if draft.mode == "append" and current_value.strip():
        if _normalize_line(suggested_text) == _normalize_line(current_value):
            return current_value
        return f"{current_value.rstrip('。')}。{suggested_text.lstrip('。')}"
    return suggested_text


def _apply_list_mode(
    *,
    current_items: list[str],
    draft: ResumeOptimizationSectionDraft,
) -> list[str]:
    suggestion_lines = _extract_apply_lines(draft.suggested_text)
    if draft.mode == "replace":
        return suggestion_lines

    merged_items = list(current_items)
    existing_keys = {_normalize_line(item) for item in current_items if item.strip()}
    for item in suggestion_lines:
        normalized = _normalize_line(item)
        if not normalized or normalized in existing_keys:
            continue
        existing_keys.add(normalized)
        merged_items.append(item)
    return merged_items


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
        resume_snapshot.basic_info.summary = _apply_summary_mode(
            current_value=resume_snapshot.basic_info.summary,
            draft=sections["summary"],
        )

    if "work_experience" in sections and sections["work_experience"].selected:
        resume_snapshot.work_experience = _apply_list_mode(
            current_items=resume_snapshot.work_experience,
            draft=sections["work_experience"],
        )

    if "projects" in sections and sections["projects"].selected:
        resume_snapshot.projects = _apply_list_mode(
            current_items=resume_snapshot.projects,
            draft=sections["projects"],
        )

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
