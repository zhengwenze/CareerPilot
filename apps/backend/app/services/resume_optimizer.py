from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.models import (
    JobDescription,
    JobReadinessEvent,
    MatchReport,
    Resume,
    ResumeOptimizationSession,
    User,
)
from app.schemas.job import JobStructuredData
from app.schemas.resume import (
    ResumeExperienceBullet,
    ResumeProjectItem,
    ResumeStructuredData,
    ResumeWorkExperienceItem,
)
from app.schemas.resume_optimization import (
    ResumeOptimizationApplyResponse,
    ResumeOptimizationContext,
    ResumeOptimizationDownstreamContract,
    ResumeOptimizationSectionDraft,
    ResumeOptimizationSessionCreateRequest,
    ResumeOptimizationSessionResponse,
    ResumeOptimizationSessionUpdateRequest,
    ResumeOptimizationTaskState,
)
from app.services.ai_client import AIClientError
from app.services.match_support import mark_reports_stale_for_resume
from app.services.resume_optimizer_ai import (
    AIResumeOptimizationPayload,
    build_resume_optimization_ai_provider,
)

TEXT_TOKEN_PATTERN = re.compile(r"[a-z0-9+#./-]+|[\u4e00-\u9fff]+", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?%?|\d+[kKwW万亿千百]?")
DATE_TOKEN_PATTERN = re.compile(r"(?:19|20)\d{2}(?:[./-](?:0?[1-9]|1[0-2]))?")
SENIORITY_ORDER = {
    "intern": 0,
    "junior": 1,
    "engineer": 2,
    "specialist": 2,
    "senior": 3,
    "lead": 4,
    "manager": 5,
    "director": 6,
    "principal": 7,
    "head": 8,
    "vp": 9,
}
SENIORITY_HINTS = {
    "实习": "intern",
    "intern": "intern",
    "junior": "junior",
    "初级": "junior",
    "engineer": "engineer",
    "工程师": "engineer",
    "specialist": "specialist",
    "专员": "specialist",
    "senior": "senior",
    "资深": "senior",
    "lead": "lead",
    "负责人": "lead",
    "manager": "manager",
    "经理": "manager",
    "director": "director",
    "总监": "director",
    "principal": "principal",
    "head": "head",
    "vp": "vp",
}
OUTCOME_INTENSITY_TERMS = (
    "主导",
    "独立负责",
    "从0到1",
    "翻倍",
    "千万级",
    "亿级",
    "显著提升",
    "大幅提升",
)


def _decimal_to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


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


def _split_lines(value: str) -> list[str]:
    return [item.strip() for item in value.splitlines() if item.strip()]


def _newline_join(items: list[str]) -> str:
    return "\n".join(item for item in items if item.strip())


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


def _score_text_match(item_text: str, query_terms: list[str]) -> int:
    normalized_item = item_text.strip()
    if not normalized_item:
        return 0
    item_tokens = _tokenize_text(normalized_item)
    score = 0
    for term in query_terms:
        normalized_term = term.strip()
        if not normalized_term:
            continue
        if normalized_term.lower() in normalized_item.lower():
            score += 3
        score += len(item_tokens & _tokenize_text(normalized_term))
    return score


def _work_anchor_text(item: ResumeWorkExperienceItem) -> str:
    bullet_text = " ".join(
        bullet.text.strip() for bullet in item.bullets if bullet.text.strip()
    )
    return " ".join(
        part
        for part in [
            item.company.strip(),
            item.title.strip(),
            item.start_date.strip(),
            item.end_date.strip(),
            bullet_text,
        ]
        if part
    ).strip()


def _project_anchor_text(item: ResumeProjectItem) -> str:
    bullet_text = " ".join(
        bullet.text.strip() for bullet in item.bullets if bullet.text.strip()
    )
    return " ".join(
        part
        for part in [
            item.name.strip(),
            item.role.strip(),
            item.start_date.strip(),
            item.end_date.strip(),
            item.summary.strip(),
            bullet_text,
        ]
        if part
    ).strip()


def _serialize_selected_tasks(
    raw_value: dict[str, Any],
) -> list[ResumeOptimizationTaskState]:
    return [
        ResumeOptimizationTaskState.model_validate(item)
        for item in raw_value.get("tasks", [])
        if isinstance(item, dict)
    ]


def _serialize_rewrite_tasks(
    raw_value: dict[str, Any],
) -> list[ResumeOptimizationTaskState]:
    return [
        ResumeOptimizationTaskState.model_validate(item)
        for item in raw_value.get("tasks", [])
        if isinstance(item, dict)
    ]


def _serialize_draft_sections(
    raw_value: dict[str, Any],
) -> dict[str, ResumeOptimizationSectionDraft]:
    sections: dict[str, ResumeOptimizationSectionDraft] = {}
    for key, value in raw_value.items():
        if isinstance(value, dict):
            sections[key] = ResumeOptimizationSectionDraft.model_validate(value)
    return sections


def _serialize_optimized_resume(
    raw_value: dict[str, Any],
) -> ResumeStructuredData | None:
    if not raw_value:
        return None
    return ResumeStructuredData.model_validate(raw_value)


def _build_downstream_contract() -> ResumeOptimizationDownstreamContract:
    return ResumeOptimizationDownstreamContract()


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
            if isinstance(item, dict) and item.get("label")
        ][:5],
    )


def _build_downloadable_file_name(
    session_record: ResumeOptimizationSession,
    optimized_resume: ResumeStructuredData | None,
) -> str | None:
    if optimized_resume is None:
        return None
    base_name = optimized_resume.basic_info.name.strip() or "resume"
    safe_name = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", base_name).strip("_")
    if not safe_name:
        safe_name = "resume"
    return f"{safe_name}_optimized_{str(session_record.id)[:8]}.md"


def serialize_resume_optimization_session(
    session_record: ResumeOptimizationSession,
    *,
    job: JobDescription,
    report: MatchReport,
) -> ResumeOptimizationSessionResponse:
    optimized_resume = _serialize_optimized_resume(
        session_record.optimized_resume_json or {}
    )
    optimized_resume_md = session_record.optimized_resume_md or ""
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
        diagnosis_json=session_record.diagnosis_json or {},
        rewrite_tasks=_serialize_rewrite_tasks(session_record.rewrite_tasks_json or {}),
        draft_sections=_serialize_draft_sections(
            session_record.draft_sections_json or {}
        ),
        selected_tasks=_serialize_selected_tasks(
            session_record.selected_tasks_json or {}
        ),
        optimized_resume_json=optimized_resume,
        fact_check_report_json=session_record.fact_check_report_json or {},
        optimized_resume_md=optimized_resume_md,
        has_downloadable_markdown=bool(optimized_resume_md.strip()),
        downloadable_file_name=_build_downloadable_file_name(
            session_record, optimized_resume
        ),
        downstream_contract=_build_downstream_contract(),
        is_stale=report.stale_status == "stale",
        created_at=session_record.created_at,
        updated_at=session_record.updated_at,
    )


def _build_task_query_terms(
    *,
    title: str,
    instruction: str,
    evidence_items: list[str],
    matched_jd_fields: dict[str, Any],
) -> list[str]:
    return _dedupe_strings(
        [
            title,
            instruction,
            *evidence_items,
            *_flatten_string_values(matched_jd_fields),
        ]
    )


def _resolve_target_section(
    *,
    requested_section: str,
    title: str,
    instruction: str,
    current_resume: ResumeStructuredData,
    evidence_items: list[str],
    matched_jd_fields: dict[str, Any],
) -> str:
    normalized = requested_section.strip().lower()
    if normalized in {"summary", "work_experience", "projects"}:
        return normalized
    combined_text = f"{title} {instruction}".lower()
    if "summary" in normalized or "摘要" in combined_text:
        return "summary"

    query_terms = _build_task_query_terms(
        title=title,
        instruction=instruction,
        evidence_items=evidence_items,
        matched_jd_fields=matched_jd_fields,
    )
    work_score = max(
        (
            _score_text_match(_work_anchor_text(item), query_terms)
            for item in current_resume.work_experience_items
        ),
        default=0,
    )
    project_score = max(
        (
            _score_text_match(_project_anchor_text(item), query_terms)
            for item in current_resume.project_items
        ),
        default=0,
    )
    if project_score > work_score:
        return "projects"
    if "项目" in combined_text:
        return "projects"
    return "work_experience"


def _select_anchor_payloads(
    *,
    section_key: str,
    current_resume: ResumeStructuredData,
    query_terms: list[str],
) -> list[dict[str, str]]:
    if section_key == "summary":
        items = [
            {"id": item.id, "text": _work_anchor_text(item)}
            for item in current_resume.work_experience_items[:2]
        ] + [
            {"id": item.id, "text": _project_anchor_text(item)}
            for item in current_resume.project_items[:1]
        ]
    elif section_key == "projects":
        items = [
            {"id": item.id, "text": _project_anchor_text(item)}
            for item in current_resume.project_items
        ]
    else:
        items = [
            {"id": item.id, "text": _work_anchor_text(item)}
            for item in current_resume.work_experience_items
        ]

    scored = [
        (item, _score_text_match(item["text"], query_terms))
        for item in items
        if item["text"].strip()
    ]
    scored = [item for item in scored if item[1] > 0]
    scored.sort(key=lambda pair: (-pair[1], pair[0]["text"].lower()))
    return [item for item, _score in scored[:2]]


def _extract_preserve_terms_from_anchor(
    *,
    section_key: str,
    anchor_ids: list[str],
    current_resume: ResumeStructuredData,
) -> list[str]:
    values: list[str] = []
    if section_key == "work_experience":
        for item in current_resume.work_experience_items:
            if item.id not in anchor_ids:
                continue
            values.extend(
                [
                    item.company,
                    item.title,
                    *[bullet.text for bullet in item.bullets[:2]],
                ]
            )
    elif section_key == "projects":
        for item in current_resume.project_items:
            if item.id not in anchor_ids:
                continue
            values.extend(
                [
                    item.name,
                    item.role,
                    item.summary,
                    *[bullet.text for bullet in item.bullets[:2]],
                ]
            )
    else:
        values.extend(
            [
                current_resume.basic_info.name,
                current_resume.basic_info.summary,
            ]
        )
    return _dedupe_strings(values)[:6]


def _build_rewrite_tasks(
    *,
    report: MatchReport,
    current_resume: ResumeStructuredData,
) -> list[ResumeOptimizationTaskState]:
    tailoring_plan = report.tailoring_plan_json or {}
    evidence_map_json = report.evidence_map_json or {}
    gap_json = report.gap_json or {}
    raw_tasks = tailoring_plan.get("rewrite_tasks") or (
        report.action_pack_json or {}
    ).get(
        "resume_tailoring_tasks",
        [],
    )
    matched_jd_fields = evidence_map_json.get("matched_jd_fields", {})
    matched_resume_fields = evidence_map_json.get("matched_resume_fields", {})
    candidate_profile = evidence_map_json.get("candidate_profile", {})
    evidence_items = _dedupe_strings(
        [
            *list(tailoring_plan.get("must_add_evidence", [])),
            *_flatten_string_values(matched_resume_fields),
            *_flatten_string_values(candidate_profile),
        ]
    )
    gap_lookup = {
        str(item.get("label")).strip(): item
        for item in gap_json.get("gaps", [])
        if isinstance(item, dict) and str(item.get("label", "")).strip()
    }

    if not raw_tasks:
        raw_tasks = [
            {
                "priority": index,
                "title": label,
                "instruction": gap_lookup[label].get("reason")
                or f"补强 {label} 相关表达",
                "target_section": "work_experience_or_projects",
            }
            for index, label in enumerate(gap_lookup.keys(), start=1)
        ]

    result: list[ResumeOptimizationTaskState] = []
    for index, raw_task in enumerate(raw_tasks, start=1):
        if not isinstance(raw_task, dict):
            continue
        title = str(raw_task.get("title") or f"改写任务 {index}").strip()
        instruction = str(raw_task.get("instruction") or "").strip()
        section_key = _resolve_target_section(
            requested_section=str(
                raw_task.get("target_section", "work_experience_or_projects")
            ),
            title=title,
            instruction=instruction,
            current_resume=current_resume,
            evidence_items=evidence_items,
            matched_jd_fields=matched_jd_fields,
        )
        query_terms = _build_task_query_terms(
            title=title,
            instruction=instruction,
            evidence_items=evidence_items,
            matched_jd_fields=matched_jd_fields,
        )
        anchors = _select_anchor_payloads(
            section_key=section_key,
            current_resume=current_resume,
            query_terms=query_terms,
        )
        gap_item = gap_lookup.get(title)
        target_requirement = (
            _dedupe_strings(
                [
                    *[
                        item
                        for item in _flatten_string_values(matched_jd_fields)
                        if _score_text_match(item, [title, instruction]) > 0
                    ],
                    *list(tailoring_plan.get("must_add_evidence", [])),
                    title,
                ]
            )[0]
            if (
                _dedupe_strings(
                    [
                        *[
                            item
                            for item in _flatten_string_values(matched_jd_fields)
                            if _score_text_match(item, [title, instruction]) > 0
                        ],
                        *list(tailoring_plan.get("must_add_evidence", [])),
                        title,
                    ]
                )
            )
            else title
        )
        available_evidence = _dedupe_strings(
            [
                *(anchor["text"] for anchor in anchors),
                *[
                    item
                    for item in evidence_items
                    if _score_text_match(item, [title, instruction, target_requirement])
                    > 0
                ],
            ]
        )[:4]
        anchor_source_ids = [anchor["id"] for anchor in anchors]
        must_preserve_terms = _extract_preserve_terms_from_anchor(
            section_key=section_key,
            anchor_ids=anchor_source_ids,
            current_resume=current_resume,
        )
        result.append(
            ResumeOptimizationTaskState(
                key=f"task-{index}",
                title=title,
                instruction=instruction
                or f"基于已验证证据强化 {target_requirement} 相关表达",
                target_section=section_key,
                target_requirement=target_requirement,
                issue=str(
                    (gap_item or {}).get("reason")
                    or f"当前简历未充分体现 {target_requirement} 对岗位的支撑。"
                ),
                available_evidence=available_evidence,
                rewrite_instruction=instruction
                or f"只基于既有事实重写 {section_key} 表达",
                risk_note=(
                    "若缺少直接证据，只能保持原事实并在诊断中提示补充，禁止新增经历、技能、数字或时间。"
                ),
                priority=int(raw_task.get("priority") or index),
                selected=True,
                anchor_source_ids=anchor_source_ids,
                rewrite_mode="replace" if section_key == "summary" else "compress",
                must_preserve_terms=must_preserve_terms,
                forbidden_terms=["资深", "专家", "Lead", "Owner", "从0到1（无证据时）"],
            )
        )
    return result


def _build_default_draft_sections(
    *,
    current_resume: ResumeStructuredData,
    optimized_resume: ResumeStructuredData,
    fact_check_report: dict[str, Any],
    selected_tasks: list[ResumeOptimizationTaskState],
) -> dict[str, ResumeOptimizationSectionDraft]:
    findings = fact_check_report.get("findings", [])
    section_findings: dict[str, list[str]] = {
        "summary": [],
        "work_experience": [],
        "projects": [],
    }
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        section_key = str(finding.get("section") or "").strip()
        if section_key in section_findings:
            section_findings[section_key].append(
                str(finding.get("message") or "").strip()
            )
    task_titles_by_section: dict[str, list[str]] = {
        "summary": [],
        "work_experience": [],
        "projects": [],
    }
    for task in selected_tasks:
        if task.selected:
            task_titles_by_section.setdefault(task.target_section, []).append(
                task.title
            )
    return {
        "summary": ResumeOptimizationSectionDraft(
            key="summary",
            label="职业摘要",
            selected=True,
            original_text=current_resume.basic_info.summary,
            suggested_text=optimized_resume.basic_info.summary,
            mode="replace",
            diagnostics=_dedupe_strings(
                [*task_titles_by_section["summary"], *section_findings["summary"]]
            ),
        ),
        "work_experience": ResumeOptimizationSectionDraft(
            key="work_experience",
            label="工作经历",
            selected=True,
            original_text=_newline_join(current_resume.work_experience),
            suggested_text=_newline_join(optimized_resume.work_experience),
            mode="replace",
            diagnostics=_dedupe_strings(
                [
                    *task_titles_by_section["work_experience"],
                    *section_findings["work_experience"],
                ]
            ),
        ),
        "projects": ResumeOptimizationSectionDraft(
            key="projects",
            label="项目经历",
            selected=True,
            original_text=_newline_join(current_resume.projects),
            suggested_text=_newline_join(optimized_resume.projects),
            mode="replace",
            diagnostics=_dedupe_strings(
                [*task_titles_by_section["projects"], *section_findings["projects"]]
            ),
        ),
    }


def _build_summary_fallback(
    *,
    current_resume: ResumeStructuredData,
    tailoring_plan_snapshot: dict[str, Any],
    selected_tasks: list[ResumeOptimizationTaskState],
) -> str:
    current_summary = current_resume.basic_info.summary.strip()
    target_role = str(tailoring_plan_snapshot.get("target_summary") or "").strip()
    evidence = _dedupe_strings(
        [item for task in selected_tasks for item in task.available_evidence]
    )
    summary_parts: list[str] = []
    if current_summary:
        summary_parts.append(current_summary.rstrip("。"))
    if target_role:
        summary_parts.append(f"目标岗位聚焦{target_role}")
    if evidence:
        summary_parts.append(f"重点保留{ '、'.join(evidence[:2]) }等已验证事实")
    summary = "；".join(part for part in summary_parts if part).strip("；")
    if not summary:
        summary = "基于现有简历事实进行岗位定向优化。"
    return summary[:180]


def _build_rule_based_optimized_resume(
    *,
    current_resume: ResumeStructuredData,
    tailoring_plan_snapshot: dict[str, Any],
    selected_tasks: list[ResumeOptimizationTaskState],
) -> ResumeStructuredData:
    optimized_resume = current_resume.model_copy(deep=True)
    optimized_resume.basic_info.summary = _build_summary_fallback(
        current_resume=current_resume,
        tailoring_plan_snapshot=tailoring_plan_snapshot,
        selected_tasks=selected_tasks,
    )
    return ResumeStructuredData.model_validate(optimized_resume.model_dump())


def _merge_ai_payload_into_resume(
    *,
    base_resume: ResumeStructuredData,
    payload: AIResumeOptimizationPayload,
) -> ResumeStructuredData:
    next_resume = base_resume.model_copy(deep=True)
    if payload.summary.strip():
        next_resume.basic_info.summary = payload.summary.strip()

    work_index = {item.id: item for item in next_resume.work_experience_items}
    for rewritten_item in payload.work_experience_items:
        target = work_index.get(rewritten_item.id)
        if target is None or not rewritten_item.bullets:
            continue
        merged_bullets: list[ResumeExperienceBullet] = []
        for index, bullet in enumerate(rewritten_item.bullets, start=1):
            merged_bullet = ResumeExperienceBullet.model_validate(
                {
                    **bullet.model_dump(),
                    "id": bullet.id or f"{target.id}_b{index}",
                    "source_refs": bullet.source_refs
                    or target.source_refs
                    or [target.id],
                }
            )
            merged_bullets.append(merged_bullet)
        target.bullets = merged_bullets

    project_index = {item.id: item for item in next_resume.project_items}
    for rewritten_item in payload.project_items:
        target = project_index.get(rewritten_item.id)
        if target is None or not rewritten_item.bullets:
            continue
        merged_bullets: list[ResumeExperienceBullet] = []
        for index, bullet in enumerate(rewritten_item.bullets, start=1):
            merged_bullet = ResumeExperienceBullet.model_validate(
                {
                    **bullet.model_dump(),
                    "id": bullet.id or f"{target.id}_b{index}",
                    "source_refs": bullet.source_refs
                    or target.source_refs
                    or [target.id],
                }
            )
            merged_bullets.append(merged_bullet)
        target.bullets = merged_bullets

    return ResumeStructuredData.model_validate(next_resume.model_dump())


def _build_job_snapshot(job: JobDescription) -> dict[str, object]:
    if job.structured_json:
        return JobStructuredData.model_validate(job.structured_json).model_dump()
    return {
        "basic": {
            "title": job.title,
            "company": job.company,
            "job_city": job.job_city,
            "employment_type": job.employment_type,
        },
        "raw_summary": job.jd_text,
    }


def _build_match_report_snapshot(report: MatchReport) -> dict[str, object]:
    return {
        "overall_score": _decimal_to_float(report.overall_score),
        "fit_band": report.fit_band,
        "gap_json": report.gap_json or {},
        "evidence_map_json": report.evidence_map_json or {},
        "tailoring_plan_json": report.tailoring_plan_json or {},
    }


def _extract_number_tokens(values: list[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        result.update(NUMBER_PATTERN.findall(value))
    return result


def _extract_date_tokens(values: list[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        result.update(DATE_TOKEN_PATTERN.findall(value))
    return result


def _extract_seniority_rank(title: str) -> int:
    normalized = title.lower()
    rank = 0
    for hint, level in SENIORITY_HINTS.items():
        if hint in normalized:
            rank = max(rank, SENIORITY_ORDER[level])
    return rank


def _build_fact_check_report(
    *,
    original_resume: ResumeStructuredData,
    optimized_resume: ResumeStructuredData,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    original_company_map = {
        item.id: (
            item.company.strip(),
            item.title.strip(),
            item.start_date.strip(),
            item.end_date.strip(),
        )
        for item in original_resume.work_experience_items
    }
    optimized_company_map = {
        item.id: (
            item.company.strip(),
            item.title.strip(),
            item.start_date.strip(),
            item.end_date.strip(),
        )
        for item in optimized_resume.work_experience_items
    }
    original_project_map = {
        item.id: (
            item.name.strip(),
            item.role.strip(),
            item.start_date.strip(),
            item.end_date.strip(),
        )
        for item in original_resume.project_items
    }
    optimized_project_map = {
        item.id: (
            item.name.strip(),
            item.role.strip(),
            item.start_date.strip(),
            item.end_date.strip(),
        )
        for item in optimized_resume.project_items
    }
    original_school_names = {
        item.school.strip()
        for item in original_resume.education_items
        if item.school.strip()
    }
    optimized_school_names = {
        item.school.strip()
        for item in optimized_resume.education_items
        if item.school.strip()
    }
    if optimized_school_names - original_school_names:
        findings.append(
            {
                "type": "new_school",
                "severity": "high",
                "section": "education",
                "message": (
                    "检测到新增学校："
                    + ", ".join(sorted(optimized_school_names - original_school_names))
                ),
            }
        )

    added_companies = {
        company
        for _item_id, (company, _title, _start, _end) in optimized_company_map.items()
        if company
        and company not in {value[0] for value in original_company_map.values()}
    }
    if added_companies:
        findings.append(
            {
                "type": "new_company",
                "severity": "high",
                "section": "work_experience",
                "message": f"检测到新增公司：{', '.join(sorted(added_companies))}",
            }
        )

    added_projects = {
        name
        for _item_id, (name, _role, _start, _end) in optimized_project_map.items()
        if name and name not in {value[0] for value in original_project_map.values()}
    }
    if added_projects:
        findings.append(
            {
                "type": "new_project",
                "severity": "high",
                "section": "projects",
                "message": f"检测到新增项目名：{', '.join(sorted(added_projects))}",
            }
        )

    original_skills = {
        skill
        for skill in [
            *original_resume.skills.technical,
            *original_resume.skills.tools,
            *original_resume.skills.languages,
        ]
        if skill.strip()
    }
    optimized_skills = {
        skill
        for skill in [
            *optimized_resume.skills.technical,
            *optimized_resume.skills.tools,
            *optimized_resume.skills.languages,
        ]
        if skill.strip()
    }
    new_skills = optimized_skills - original_skills
    if new_skills:
        findings.append(
            {
                "type": "new_skill",
                "severity": "high",
                "section": "skills",
                "message": f"检测到新增技能：{', '.join(sorted(new_skills))}",
            }
        )

    original_texts = [
        original_resume.basic_info.summary,
        *original_resume.education,
        *original_resume.work_experience,
        *original_resume.projects,
        *original_resume.certifications,
    ]
    optimized_texts = [
        optimized_resume.basic_info.summary,
        *optimized_resume.education,
        *optimized_resume.work_experience,
        *optimized_resume.projects,
        *optimized_resume.certifications,
    ]
    new_numbers = _extract_number_tokens(optimized_texts) - _extract_number_tokens(
        original_texts
    )
    if new_numbers:
        findings.append(
            {
                "type": "new_number",
                "severity": "high",
                "section": "summary",
                "message": f"检测到新增数字或比例：{', '.join(sorted(new_numbers))}",
            }
        )

    for item_id, optimized_fields in optimized_company_map.items():
        original_fields = original_company_map.get(item_id)
        if original_fields is None:
            continue
        original_company, original_title, original_start, original_end = original_fields
        optimized_company, optimized_title, optimized_start, optimized_end = (
            optimized_fields
        )
        if (
            optimized_company != original_company
            or optimized_start != original_start
            or optimized_end != original_end
        ):
            findings.append(
                {
                    "type": "timeline_or_identity_change",
                    "severity": "high",
                    "section": "work_experience",
                    "message": f"工作经历 {item_id} 出现公司或时间改动，需要人工复核。",
                }
            )
        if _extract_seniority_rank(optimized_title) > _extract_seniority_rank(
            original_title
        ):
            findings.append(
                {
                    "type": "title_inflation",
                    "severity": "medium",
                    "section": "work_experience",
                    "message": (
                        "工作经历 "
                        + f"{item_id}"
                        + " 的职级表达可能被夸大："
                        + f"{original_title} -> {optimized_title}"
                    ),
                }
            )

    for item_id, optimized_fields in optimized_project_map.items():
        original_fields = original_project_map.get(item_id)
        if original_fields is None:
            continue
        original_name, _original_role, original_start, original_end = original_fields
        optimized_name, _optimized_role, optimized_start, optimized_end = (
            optimized_fields
        )
        if (
            optimized_name != original_name
            or optimized_start != original_start
            or optimized_end != original_end
        ):
            findings.append(
                {
                    "type": "project_identity_change",
                    "severity": "high",
                    "section": "projects",
                    "message": f"项目经历 {item_id} 出现名称或时间改动，需要人工复核。",
                }
            )

    original_bullet_text = " ".join(
        bullet.text
        for item in original_resume.work_experience_items
        + original_resume.project_items
        for bullet in item.bullets
    )
    optimized_bullet_text = " ".join(
        bullet.text
        for item in optimized_resume.work_experience_items
        + optimized_resume.project_items
        for bullet in item.bullets
    )
    for term in OUTCOME_INTENSITY_TERMS:
        if term in optimized_bullet_text and term not in original_bullet_text:
            findings.append(
                {
                    "type": "outcome_intensity",
                    "severity": "medium",
                    "section": "work_experience",
                    "message": f"检测到新增成果强度措辞：{term}",
                }
            )

    for item in optimized_resume.work_experience_items + optimized_resume.project_items:
        for bullet in item.bullets:
            extra_skills = {
                skill
                for skill in bullet.skills_used
                if skill.strip() and skill not in original_skills
            }
            if extra_skills:
                findings.append(
                    {
                        "type": "skill_attribution",
                        "severity": "medium",
                        "section": (
                            "projects"
                            if isinstance(item, ResumeProjectItem)
                            else "work_experience"
                        ),
                        "message": f"{item.id} 存在新增技能归属：{', '.join(sorted(extra_skills))}",
                    }
                )

    for collection_name, items in {
        "education": optimized_resume.education_items,
        "work_experience": optimized_resume.work_experience_items,
        "projects": optimized_resume.project_items,
    }.items():
        for item in items:
            start_date = getattr(item, "start_date", "")
            end_date = getattr(item, "end_date", "")
            if start_date and end_date and start_date > end_date:
                findings.append(
                    {
                        "type": "timeline_conflict",
                        "severity": "high",
                        "section": collection_name,
                        "message": (
                            collection_name
                            + " 中存在开始时间晚于结束时间的记录："
                            + getattr(item, "id", "")
                        ),
                    }
                )

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for finding in findings:
        severity = str(finding.get("severity") or "low")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "summary": {
            "high_risk_count": severity_counts.get("high", 0),
            "medium_risk_count": severity_counts.get("medium", 0),
            "passed": severity_counts.get("high", 0) == 0,
        },
        "findings": findings,
    }


def build_resume_fact_check_report(
    *,
    original_resume: ResumeStructuredData,
    optimized_resume: ResumeStructuredData,
) -> dict[str, Any]:
    return _build_fact_check_report(
        original_resume=original_resume,
        optimized_resume=optimized_resume,
    )


def _render_markdown_header(resume: ResumeStructuredData) -> list[str]:
    lines = [f"# {resume.basic_info.name.strip() or 'Candidate'}", ""]
    contact_line = " | ".join(
        item
        for item in [
            resume.basic_info.email.strip(),
            resume.basic_info.phone.strip(),
            resume.basic_info.location.strip(),
        ]
        if item
    )
    if contact_line:
        lines.extend([contact_line, ""])
    return lines


def _render_markdown_section(title: str, body_lines: list[str]) -> list[str]:
    if not any(line.strip() for line in body_lines):
        return []
    return [f"## {title}", "", *body_lines, ""]


def _render_education_markdown(resume: ResumeStructuredData) -> list[str]:
    lines: list[str] = []
    if resume.education_items:
        for item in resume.education_items:
            header = " | ".join(
                value
                for value in [
                    item.school.strip(),
                    " ".join(
                        value
                        for value in [item.major.strip(), item.degree.strip()]
                        if value
                    ).strip(),
                    " - ".join(
                        value
                        for value in [item.start_date.strip(), item.end_date.strip()]
                        if value
                    ).strip(),
                ]
                if value
            )
            if header:
                lines.append(f"- {header}")
            for honor in item.honors:
                if honor.strip():
                    lines.append(f"  - {honor.strip()}")
    else:
        lines.extend(f"- {value}" for value in resume.education if value.strip())
    return lines


def _render_experience_items_markdown(
    items: list[ResumeWorkExperienceItem],
) -> list[str]:
    lines: list[str] = []
    for item in items:
        header = " | ".join(
            value
            for value in [
                item.company.strip(),
                item.title.strip(),
                " - ".join(
                    value
                    for value in [item.start_date.strip(), item.end_date.strip()]
                    if value
                ).strip(),
                item.location.strip(),
            ]
            if value
        )
        if header:
            lines.append(f"### {header}")
        for bullet in item.bullets:
            if bullet.text.strip():
                lines.append(f"- {bullet.text.strip()}")
        lines.append("")
    return lines[:-1] if lines and lines[-1] == "" else lines


def _render_project_items_markdown(
    items: list[ResumeProjectItem],
) -> list[str]:
    lines: list[str] = []
    for item in items:
        header = " | ".join(
            value
            for value in [
                item.name.strip(),
                item.role.strip(),
                " - ".join(
                    value
                    for value in [item.start_date.strip(), item.end_date.strip()]
                    if value
                ).strip(),
            ]
            if value
        )
        if header:
            lines.append(f"### {header}")
        if item.summary.strip():
            lines.append(item.summary.strip())
        for bullet in item.bullets:
            if bullet.text.strip():
                lines.append(f"- {bullet.text.strip()}")
        lines.append("")
    return lines[:-1] if lines and lines[-1] == "" else lines


def _render_skills_markdown(resume: ResumeStructuredData) -> list[str]:
    groups = [
        ("Technical", resume.skills.technical),
        ("Tools", resume.skills.tools),
        ("Languages", resume.skills.languages),
    ]
    lines: list[str] = []
    for label, values in groups:
        items = [value.strip() for value in values if value.strip()]
        if not items:
            continue
        lines.append(f"- {label}: {', '.join(items)}")
    return lines


def render_optimized_resume_markdown(resume: ResumeStructuredData) -> str:
    lines: list[str] = []
    lines.extend(_render_markdown_header(resume))
    if resume.basic_info.summary.strip():
        lines.extend(
            _render_markdown_section("Summary", [resume.basic_info.summary.strip()])
        )
    lines.extend(
        _render_markdown_section("Education", _render_education_markdown(resume))
    )
    lines.extend(
        _render_markdown_section(
            "Work Experience",
            _render_experience_items_markdown(resume.work_experience_items),
        )
    )
    lines.extend(
        _render_markdown_section(
            "Projects",
            _render_project_items_markdown(resume.project_items),
        )
    )
    lines.extend(_render_markdown_section("Skills", _render_skills_markdown(resume)))
    lines.extend(
        _render_markdown_section(
            "Certifications",
            [f"- {value}" for value in resume.certifications if value.strip()],
        )
    )
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def _build_diagnosis_json(
    *,
    report: MatchReport,
    tailoring_plan_snapshot: dict[str, Any],
    rewrite_tasks: list[ResumeOptimizationTaskState],
    fact_check_report: dict[str, Any] | None = None,
    ai_status: str = "not_run",
    ai_reason: str = "",
) -> dict[str, Any]:
    gap_json = report.gap_json or {}
    findings_summary = (fact_check_report or {}).get("summary", {})
    return {
        "target_role": tailoring_plan_snapshot.get("target_summary"),
        "overall_score": _decimal_to_float(report.overall_score),
        "fit_band": report.fit_band,
        "top_gaps": [
            {
                "label": item.get("label"),
                "reason": item.get("reason"),
                "severity": item.get("severity"),
            }
            for item in gap_json.get("gaps", [])
            if isinstance(item, dict)
        ][:5],
        "must_add_evidence": list(tailoring_plan_snapshot.get("must_add_evidence", [])),
        "missing_info_questions": list(
            tailoring_plan_snapshot.get("missing_info_questions", [])
        ),
        "rewrite_task_count": len(rewrite_tasks),
        "ai_status": {"status": ai_status, "reason": ai_reason},
        "session_rules": {
            "status_flow": ["draft", "ready", "applied"],
            "ready_requires": [
                "rewrite_tasks_json",
                "draft_sections_json",
                "optimized_resume_json",
                "optimized_resume_md",
            ],
            "apply_effect": (
                "optimized_resume_json is written into resume.structured_json "
                "and increments resume.latest_version"
            ),
            "match_report_after_apply": "related match reports become stale",
        },
        "downstream_contract": _build_downstream_contract().model_dump(),
        "fact_check_summary": findings_summary,
    }


async def _generate_optimized_resume_artifacts(
    *,
    current_resume: ResumeStructuredData,
    job: JobDescription,
    report: MatchReport,
    tailoring_plan_snapshot: dict[str, Any],
    selected_tasks: list[ResumeOptimizationTaskState],
    settings: Settings | None,
) -> tuple[
    ResumeStructuredData,
    dict[str, Any],
    dict[str, ResumeOptimizationSectionDraft],
    dict[str, Any],
    str,
]:
    fallback_resume = _build_rule_based_optimized_resume(
        current_resume=current_resume,
        tailoring_plan_snapshot=tailoring_plan_snapshot,
        selected_tasks=selected_tasks,
    )
    optimized_resume = fallback_resume
    ai_status = "skipped"
    ai_reason = "AI provider unavailable or disabled"
    provider = build_resume_optimization_ai_provider(settings)
    try:
        ai_result = await provider.rewrite(
            payload={
                "source_resume": current_resume.model_dump(),
                "job_snapshot": _build_job_snapshot(job),
                "match_report_snapshot": _build_match_report_snapshot(report),
                "rewrite_tasks": [
                    task.model_dump() for task in selected_tasks if task.selected
                ],
            }
        )
        ai_status = ai_result.status
        ai_reason = ai_result.reason
        if ai_result.payload is not None:
            optimized_resume = _merge_ai_payload_into_resume(
                base_resume=fallback_resume,
                payload=ai_result.payload,
            )
    except AIClientError as exc:
        ai_status = "fallback"
        ai_reason = exc.detail

    fact_check_report = _build_fact_check_report(
        original_resume=current_resume,
        optimized_resume=optimized_resume,
    )
    draft_sections = _build_default_draft_sections(
        current_resume=current_resume,
        optimized_resume=optimized_resume,
        fact_check_report=fact_check_report,
        selected_tasks=selected_tasks,
    )
    diagnosis_json = _build_diagnosis_json(
        report=report,
        tailoring_plan_snapshot=tailoring_plan_snapshot,
        rewrite_tasks=selected_tasks,
        fact_check_report=fact_check_report,
        ai_status=ai_status,
        ai_reason=ai_reason,
    )
    optimized_resume_md = render_optimized_resume_markdown(optimized_resume)
    return (
        optimized_resume,
        diagnosis_json,
        draft_sections,
        fact_check_report,
        optimized_resume_md,
    )


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
    report = await _get_match_report_or_404(
        session,
        current_user=current_user,
        report_id=payload.match_report_id,
    )
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
    rewrite_tasks = _build_rewrite_tasks(report=report, current_resume=resume_snapshot)
    initial_resume = _build_rule_based_optimized_resume(
        current_resume=resume_snapshot,
        tailoring_plan_snapshot=report.tailoring_plan_json or {},
        selected_tasks=rewrite_tasks,
    )
    initial_fact_check = _build_fact_check_report(
        original_resume=resume_snapshot,
        optimized_resume=initial_resume,
    )
    initial_draft_sections = _build_default_draft_sections(
        current_resume=resume_snapshot,
        optimized_resume=initial_resume,
        fact_check_report=initial_fact_check,
        selected_tasks=rewrite_tasks,
    )
    session_record = ResumeOptimizationSession(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        source_resume_version=report.resume_version,
        source_job_version=report.job_version,
        applied_resume_version=None,
        status="draft",
        diagnosis_json=_build_diagnosis_json(
            report=report,
            tailoring_plan_snapshot=report.tailoring_plan_json or {},
            rewrite_tasks=rewrite_tasks,
            fact_check_report=initial_fact_check,
            ai_status="not_run",
            ai_reason="Session created before suggestion generation",
        ),
        tailoring_plan_snapshot_json=report.tailoring_plan_json or {},
        rewrite_tasks_json={"tasks": [item.model_dump() for item in rewrite_tasks]},
        draft_sections_json={
            key: value.model_dump() for key, value in initial_draft_sections.items()
        },
        selected_tasks_json={"tasks": [item.model_dump() for item in rewrite_tasks]},
        optimized_resume_json=initial_resume.model_dump(),
        fact_check_report_json=initial_fact_check,
        optimized_resume_md="",
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
    settings: Settings | None = None,
) -> ResumeOptimizationSessionResponse:
    session_record, resume, job, report = await _load_session_bundle(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    current_resume = ResumeStructuredData.model_validate(resume.structured_json or {})
    selected_tasks = _serialize_selected_tasks(session_record.selected_tasks_json or {})
    if not selected_tasks:
        selected_tasks = _build_rewrite_tasks(
            report=report, current_resume=current_resume
        )

    (
        optimized_resume,
        diagnosis_json,
        draft_sections,
        fact_check_report,
        optimized_resume_md,
    ) = await _generate_optimized_resume_artifacts(
        current_resume=current_resume,
        job=job,
        report=report,
        tailoring_plan_snapshot=session_record.tailoring_plan_snapshot_json or {},
        selected_tasks=selected_tasks,
        settings=settings,
    )

    session_record.rewrite_tasks_json = {
        "tasks": [item.model_dump() for item in selected_tasks]
    }
    session_record.selected_tasks_json = {
        "tasks": [item.model_dump() for item in selected_tasks]
    }
    session_record.diagnosis_json = diagnosis_json
    session_record.draft_sections_json = {
        key: value.model_dump() for key, value in draft_sections.items()
    }
    session_record.optimized_resume_json = optimized_resume.model_dump()
    session_record.fact_check_report_json = fact_check_report
    session_record.optimized_resume_md = optimized_resume_md
    session_record.status = "ready"
    session_record.updated_by = current_user.id
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return serialize_resume_optimization_session(session_record, job=job, report=report)


def _resume_from_draft_sections(
    *,
    current_resume: ResumeStructuredData,
    draft_sections: dict[str, ResumeOptimizationSectionDraft],
) -> ResumeStructuredData:
    next_resume = current_resume.model_copy(deep=True)
    summary_draft = draft_sections.get("summary")
    if summary_draft is not None and summary_draft.selected:
        next_resume.basic_info.summary = summary_draft.suggested_text.strip()
    work_draft = draft_sections.get("work_experience")
    if work_draft is not None and work_draft.selected:
        next_resume.work_experience = _split_lines(work_draft.suggested_text)
    project_draft = draft_sections.get("projects")
    if project_draft is not None and project_draft.selected:
        next_resume.projects = _split_lines(project_draft.suggested_text)
    return ResumeStructuredData.model_validate(next_resume.model_dump())


async def update_resume_optimization_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    payload: ResumeOptimizationSessionUpdateRequest,
) -> ResumeOptimizationSessionResponse:
    session_record, resume, job, report = await _load_session_bundle(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    current_resume = ResumeStructuredData.model_validate(resume.structured_json or {})
    optimized_resume = _resume_from_draft_sections(
        current_resume=current_resume,
        draft_sections=payload.draft_sections,
    )
    fact_check_report = _build_fact_check_report(
        original_resume=current_resume,
        optimized_resume=optimized_resume,
    )
    diagnosis_json = _build_diagnosis_json(
        report=report,
        tailoring_plan_snapshot=session_record.tailoring_plan_snapshot_json or {},
        rewrite_tasks=payload.selected_tasks,
        fact_check_report=fact_check_report,
        ai_status="manual_update",
        ai_reason="Draft sections were updated manually",
    )
    session_record.draft_sections_json = {
        key: value.model_dump() for key, value in payload.draft_sections.items()
    }
    session_record.selected_tasks_json = {
        "tasks": [item.model_dump() for item in payload.selected_tasks]
    }
    session_record.rewrite_tasks_json = {
        "tasks": [item.model_dump() for item in payload.selected_tasks]
    }
    session_record.diagnosis_json = diagnosis_json
    session_record.optimized_resume_json = optimized_resume.model_dump()
    session_record.fact_check_report_json = fact_check_report
    session_record.optimized_resume_md = render_optimized_resume_markdown(
        optimized_resume
    )
    session_record.status = "ready"
    session_record.updated_by = current_user.id
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return serialize_resume_optimization_session(session_record, job=job, report=report)


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
    if (
        session_record.status == "applied"
        and session_record.applied_resume_version is not None
    ):
        return ResumeOptimizationApplyResponse(
            session_id=session_record.id,
            resume_id=resume.id,
            applied_resume_version=session_record.applied_resume_version,
        )

    optimized_resume = _serialize_optimized_resume(
        session_record.optimized_resume_json or {}
    )
    if optimized_resume is None:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Optimization session does not have a structured optimized resume yet",
        )
    if not (session_record.optimized_resume_md or "").strip():
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message=(
                "Optimization session is not ready for apply "
                "because markdown output is missing"
            ),
        )

    resume.structured_json = optimized_resume.model_dump()
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
            reason="Structured resume optimization was applied to resume.structured_json",
            metadata_json={
                "session_id": str(session_record.id),
                "resume_version": resume.latest_version,
                "report_id": str(report.id),
                "downstream_fact_source": "resume.structured_json",
                "optimized_resume_json_available": True,
                "optimized_resume_md_is_fact_source": False,
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
        downstream_fact_source="resume.structured_json",
    )


async def get_resume_optimization_markdown_download(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> tuple[str, str]:
    session_record, _resume, job, report = await _load_session_bundle(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    payload = serialize_resume_optimization_session(
        session_record, job=job, report=report
    )
    tailored_markdown = (session_record.tailored_resume_md or "").strip()
    if tailored_markdown:
        return tailored_markdown, payload.downloadable_file_name or "tailored_resume.md"
    if not payload.optimized_resume_md.strip():
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Optimized markdown resume is not ready yet",
        )
    return (
        payload.optimized_resume_md,
        payload.downloadable_file_name or "optimized_resume.md",
    )
