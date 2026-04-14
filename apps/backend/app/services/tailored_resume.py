from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import desc, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.models import (
    JobDescription,
    MatchReport,
    Resume,
    ResumeOptimizationSession,
    User,
)
from app.schemas.job import JobCreateRequest, JobUpdateRequest
from app.schemas.match_report import MatchReportCreateRequest
from app.schemas.ai_runtime import ContentChangeItem, ContentSegment, SegmentExplanation, TaskState
from app.schemas.resume import (
    ResumeCertificationItem,
    ResumeEducationItem,
    ResumeExperienceBullet,
    ResumeProjectItem,
    ResumeStructuredData,
    ResumeWorkExperienceItem,
)
from app.schemas.resume_optimization import ResumeOptimizationSessionCreateRequest
from app.schemas.tailored_resume import (
    TailoredResumeArtifactResponse,
    TailoredResumeAudit,
    TailoredResumeBasic,
    TailoredResumeCustomSection,
    TailoredResumeDocument,
    TailoredResumeDisplayStatus,
    TailoredResumeEducationItem,
    TailoredResumeExperienceItem,
    TailoredResumeGenerateRequest,
    TailoredResumeGenerateFromSavedJobRequest,
    TailoredResumeMatchSummary,
    TailoredResumeProjectItem,
    TailoredResumeWorkflowResponse,
)
from app.services.ai_client import AIClientError, AIProviderConfig, request_json_completion
from app.services.resume_ai import is_ai_configured
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
from app.services.resume_markdown_renderer import render_resume_markdown
from app.services.resume_optimizer import (
    build_resume_fact_check_report,
    create_resume_optimization_session,
)
from app.prompts.tailored_resume import (
    get_tailored_resume_rewrite_prompt,
)
from app.services.tailored_resume_document_ai import (
    AITailoredResumeDocumentRequest,
    build_tailored_resume_document_ai_provider,
)

TOKEN_PATTERN = re.compile(r"[a-z0-9+#./-]+|[\u4e00-\u9fff]+", re.IGNORECASE)
TAILORED_RESUME_SEGMENT_ORDER: tuple[tuple[str, str], ...] = (
    ("summary", "职业摘要"),
    ("skills", "技能聚焦"),
    ("experience", "工作经历"),
    ("projects", "项目经历"),
    ("additional", "教育与补充信息"),
)
TASK_STATE_STATUSES = {
    "pending",
    "processing",
    "success",
    "failed",
    "ready",
    "cancelled",
    "returned",
    "aborted",
}
SEGMENT_STATUSES = {
    "pending",
    "processing",
    "success",
    "failed",
    "cancelled",
    "returned",
    "aborted",
}
TERMINAL_TASK_STATUSES = {"success", "failed", "ready", "cancelled", "returned", "aborted"}
RETRYABLE_DISPLAY_STATUSES = {"failed", "empty_result", "cancelled", "returned", "aborted"}
DISPLAY_TERMINAL_STATUSES = {"success", "failed", "cancelled", "returned", "aborted", "empty_result"}

logger = logging.getLogger(__name__)


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class _RewriteOnlyBullet(BaseModel):
    id: str
    text: str = ""
    kind: str = "responsibility"
    metrics: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class _RewriteOnlyWorkItem(BaseModel):
    id: str
    bullets: list[_RewriteOnlyBullet] = Field(default_factory=list)


class _RewriteOnlyProjectItem(BaseModel):
    id: str
    bullets: list[_RewriteOnlyBullet] = Field(default_factory=list)


class _RewriteOnlyResponse(BaseModel):
    summary: str = ""
    work_experience_items: list[_RewriteOnlyWorkItem] = Field(default_factory=list)
    project_items: list[_RewriteOnlyProjectItem] = Field(default_factory=list)
    unresolved_items: list[dict[str, str]] = Field(default_factory=list)
    editor_notes: list[str] = Field(default_factory=list)


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


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _join_non_empty(parts: list[str | None], *, separator: str = " / ") -> str:
    return separator.join(part.strip() for part in parts if part and part.strip())


def _serialize_task_state(state: TaskState | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(state, TaskState):
        return state.model_dump(mode="json")
    if isinstance(state, dict):
        return _deserialize_task_state(state).model_dump(mode="json")
    return TaskState().model_dump(mode="json")


def _normalize_task_state_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "canceled": "cancelled",
        "complete": "success",
        "completed": "success",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in TASK_STATE_STATUSES else "pending"


def _normalize_segment_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {"canceled": "cancelled"}
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in SEGMENT_STATUSES else "pending"


def _normalize_session_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "queued": "processing",
        "canceled": "cancelled",
        "complete": "success",
        "completed": "success",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in TASK_STATE_STATUSES:
        return normalized
    if normalized in {"draft", ""}:
        return "pending"
    return "pending"


def _deserialize_task_state(payload: dict[str, Any] | None) -> TaskState:
    data = dict(payload or {})
    data["status"] = _normalize_task_state_status(data.get("status"))
    try:
        return TaskState.model_validate(data)
    except ValidationError:
        return TaskState(
            status=_normalize_task_state_status(data.get("status")),
            phase=str(data.get("phase") or ""),
            message=str(data.get("message") or ""),
        )


def _serialize_segment(segment: ContentSegment | dict[str, Any]) -> dict[str, Any]:
    if isinstance(segment, ContentSegment):
        return segment.model_dump(mode="json")
    data = dict(segment)
    data["status"] = _normalize_segment_status(data.get("status"))
    return ContentSegment.model_validate(data).model_dump(mode="json")


def _deserialize_segments(payload: dict[str, Any] | list[Any] | None) -> list[ContentSegment]:
    items: list[ContentSegment] = []
    if isinstance(payload, dict):
        for value in payload.values():
            data = dict(value) if isinstance(value, dict) else {}
            data["status"] = _normalize_segment_status(data.get("status"))
            try:
                items.append(ContentSegment.model_validate(data))
            except ValidationError:
                continue
    elif isinstance(payload, list):
        for value in payload:
            data = dict(value) if isinstance(value, dict) else {}
            data["status"] = _normalize_segment_status(data.get("status"))
            try:
                items.append(ContentSegment.model_validate(data))
            except ValidationError:
                continue
    return sorted(items, key=lambda item: (item.sequence, item.key))


def _serialize_segments(items: list[ContentSegment]) -> dict[str, Any]:
    return {item.key: item.model_dump(mode="json") for item in items}


def _append_event(container: dict[str, Any], *, event_type: str, payload: dict[str, Any] | None = None) -> None:
    events = list(container.get("events") or [])
    events.append(
        {
            "event_type": event_type,
            "occurred_at": utc_now_naive().isoformat(),
            "payload": payload or {},
        }
    )
    container["events"] = events[-50:]


def _mark_task_state(
    session_record: ResumeOptimizationSession,
    *,
    status: str,
    phase: str,
    message: str,
    current_step: int | None = None,
    total_steps: int | None = None,
) -> TaskState:
    state = _deserialize_task_state(session_record.diagnosis_json)
    now = utc_now_naive()
    if state.started_at is None and status in {"processing", *TERMINAL_TASK_STATUSES}:
        state.started_at = now
    state.status = _normalize_task_state_status(status)  # type: ignore[assignment]
    state.phase = phase
    state.message = message
    state.last_updated_at = now
    if current_step is not None:
        state.current_step = current_step
    if total_steps is not None:
        state.total_steps = total_steps
    if status in TERMINAL_TASK_STATUSES:
        state.completed_at = now
    session_record.diagnosis_json = _serialize_task_state(state)
    return state


def _store_segment(
    session_record: ResumeOptimizationSession,
    *,
    segment: ContentSegment,
) -> list[ContentSegment]:
    items = _deserialize_segments(session_record.draft_sections_json)
    by_key = {item.key: item for item in items}
    by_key[segment.key] = segment
    updated = sorted(by_key.values(), key=lambda item: (item.sequence, item.key))
    session_record.draft_sections_json = _serialize_segments(updated)
    return updated


def _resolve_user_id(current_user: User) -> UUID:
    identity = inspect(current_user).identity
    if identity:
        return identity[0]
    return current_user.id


def _dedupe_strings(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = _normalize_text(item).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(_normalize_text(item))
    return result


def _structured_top_level_keys(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    return sorted(value.keys())


def _resume_has_structured_signal(resume_data: ResumeStructuredData) -> bool:
    return any(
        [
            bool(_normalize_text(resume_data.basic_info.name)),
            bool(_normalize_text(resume_data.basic_info.summary)),
            bool(resume_data.education_items),
            bool(resume_data.work_experience_items),
            bool(resume_data.project_items),
            bool(_dedupe_strings(resume_data.skills.technical)),
            bool(_dedupe_strings(resume_data.skills.tools)),
            bool(_dedupe_strings(resume_data.skills.languages)),
            bool(resume_data.certification_items),
            bool(_dedupe_strings(resume_data.awards)),
            bool(resume_data.custom_sections),
        ]
    )


def _resume_input_snapshot(resume: Resume) -> dict[str, Any]:
    canonical_resume_md = _extract_original_resume_markdown(resume)
    raw_text = str(resume.raw_text or "").strip()
    structured_payload = resume.structured_json if isinstance(resume.structured_json, dict) else None
    return {
        "resume_id": resume.id,
        "parse_status": resume.parse_status,
        "structured_json_empty": not bool(structured_payload),
        "structured_json_keys": _structured_top_level_keys(structured_payload),
        "canonical_resume_md_present": bool(canonical_resume_md),
        "canonical_resume_md_len": len(canonical_resume_md),
        "raw_text_present": bool(raw_text),
        "raw_text_len": len(raw_text),
    }


def _validate_structured_resume_payload(
    payload: dict[str, Any] | None,
) -> tuple[ResumeStructuredData | None, str | None]:
    if not isinstance(payload, dict) or not payload:
        return None, "missing"
    try:
        structured = ResumeStructuredData.model_validate(payload)
    except ValidationError:
        return None, "invalid"
    if not _resume_has_structured_signal(structured):
        return None, "empty"
    return structured, None


def _flatten_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        normalized = _normalize_text(value)
        return [normalized] if normalized else []
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


def _tokenize_keywords(value: str) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_PATTERN.findall(value.lower()):
        normalized = token.strip()
        if not normalized:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", normalized):
            if len(normalized) >= 2:
                tokens.append(normalized)
            continue
        if len(normalized) >= 2:
            tokens.append(normalized)
    return tokens


def _keyword_supported(keyword: str, evidence_text: str) -> bool:
    normalized_keyword = keyword.strip().lower()
    if not normalized_keyword:
        return False
    evidence_lower = evidence_text.lower()
    if normalized_keyword in evidence_lower:
        return True
    keyword_tokens = set(_tokenize_keywords(normalized_keyword))
    evidence_tokens = set(_tokenize_keywords(evidence_text))
    return bool(keyword_tokens and keyword_tokens <= evidence_tokens)


def _extract_original_resume_markdown(resume: Resume) -> str:
    artifacts = resume.parse_artifacts_json or {}
    canonical_markdown = str(artifacts.get("canonical_resume_md") or "").strip()
    if canonical_markdown:
        return canonical_markdown
    raw_text = str(resume.raw_text or "").strip()
    if raw_text:
        return raw_text

    structured = ResumeStructuredData.model_validate(resume.structured_json or {})
    markdown = render_resume_markdown(structured).strip()
    if markdown:
        return markdown
    return f"# {structured.basic_info.name.strip() or resume.file_name}"


def _extract_job_keywords(job: JobDescription, report: MatchReport) -> list[str]:
    evidence_map_json = report.evidence_map_json or {}
    matched_jd_fields = evidence_map_json.get("matched_jd_fields", {})
    collected = [
        job.title,
        *(_flatten_string_values(matched_jd_fields)),
    ]
    return _dedupe_strings(collected)[:12]


def _build_document_from_structured_resume(
    *,
    resume_data: ResumeStructuredData,
    job: JobDescription,
    job_keywords: list[str],
    warnings: list[str] | None = None,
) -> TailoredResumeDocument:
    evidence_text = "\n".join(_flatten_string_values(resume_data.model_dump()))
    matched_keywords = [
        keyword for keyword in job_keywords if _keyword_supported(keyword, evidence_text)
    ]
    missing_keywords = [keyword for keyword in job_keywords if keyword not in matched_keywords]
    return TailoredResumeDocument(
        matchSummary=TailoredResumeMatchSummary(
            targetRole=job.title or "",
            optimizationLevel="conservative",
            matchedKeywords=matched_keywords[:8],
            missingButImportantKeywords=missing_keywords[:8],
            overallStrategy="在不新增事实的前提下，优先强化与目标岗位直接相关的表达。",
        ),
        basic=TailoredResumeBasic(
            name=resume_data.basic_info.name,
            title=resume_data.basic_info.title or job.title or resume_data.basic_info.summary,
            email=resume_data.basic_info.email,
            phone=resume_data.basic_info.phone,
            location=resume_data.basic_info.location,
            links=resume_data.basic_info.links,
        ),
        summary=resume_data.basic_info.summary,
        education=[
            TailoredResumeEducationItem(
                school=item.school,
                major=item.major,
                degree=item.degree,
                startDate=item.start_date,
                endDate=item.end_date,
                description=_dedupe_strings(item.honors),
            )
            for item in resume_data.education_items
        ],
        experience=[
            TailoredResumeExperienceItem(
                company=item.company,
                position=item.title,
                startDate=item.start_date,
                endDate=item.end_date,
                bullets=[bullet.text for bullet in item.bullets if bullet.text.strip()],
            )
            for item in resume_data.work_experience_items
        ],
        projects=[
            TailoredResumeProjectItem(
                name=item.name,
                role=item.role,
                startDate=item.start_date,
                endDate=item.end_date,
                bullets=_dedupe_strings(
                    [item.summary, *[bullet.text for bullet in item.bullets if bullet.text.strip()]]
                ),
                link="",
            )
            for item in resume_data.project_items
        ],
        skills=_dedupe_strings([*resume_data.skills.technical, *resume_data.skills.tools]),
        certificates=_dedupe_strings(resume_data.certifications),
        languages=_dedupe_strings(resume_data.skills.languages),
        awards=_dedupe_strings(resume_data.awards),
        customSections=[
            TailoredResumeCustomSection(
                title=section.title,
                items=[
                    {
                        "title": item.title,
                        "subtitle": item.subtitle,
                        "years": item.years,
                        "description": item.description,
                    }
                    for item in section.items
                ],
            )
            for section in resume_data.custom_sections
        ],
        audit=TailoredResumeAudit(
            truthfulnessStatus="warning" if warnings else "passed",
            warnings=warnings or [],
            changedSections=[],
            addedKeywordsOnlyFromEvidence=True,
        ),
    )


def _build_summary_text(item: ResumeStructuredData) -> str:
    return (item.basic_info.summary or "").strip()


def _build_experience_text(item: ResumeStructuredData) -> str:
    lines: list[str] = []
    for work in item.work_experience_items:
        header = " | ".join(part for part in [work.company, work.title, work.start_date, work.end_date] if part)
        if header:
            lines.append(f"- {header}")
        for bullet in work.bullets:
            if bullet.text.strip():
                lines.append(f"  - {bullet.text.strip()}")
    return "\n".join(lines).strip()


def _build_projects_text(item: ResumeStructuredData) -> str:
    lines: list[str] = []
    for project in item.project_items:
        header = " | ".join(
            part for part in [project.name, project.role, project.start_date, project.end_date] if part
        )
        if header:
            lines.append(f"- {header}")
        if project.summary.strip():
            lines.append(f"  - {project.summary.strip()}")
        for bullet in project.bullets:
            if bullet.text.strip():
                lines.append(f"  - {bullet.text.strip()}")
    return "\n".join(lines).strip()


def _build_skills_text(item: ResumeStructuredData) -> str:
    lines: list[str] = []
    if item.skills.technical:
        lines.append(f"技术：{', '.join(item.skills.technical)}")
    if item.skills.tools:
        lines.append(f"工具：{', '.join(item.skills.tools)}")
    if item.skills.languages:
        lines.append(f"语言：{', '.join(item.skills.languages)}")
    return "\n".join(lines).strip()


def _build_additional_text(item: ResumeStructuredData) -> str:
    lines: list[str] = []
    for edu in item.education_items:
        value = " | ".join(part for part in [edu.school, edu.major, edu.degree, edu.start_date, edu.end_date] if part)
        if value:
            lines.append(f"教育：{value}")
    for cert in item.certification_items:
        value = " | ".join(part for part in [cert.name, cert.issuer, cert.date] if part)
        if value:
            lines.append(f"证书：{value}")
    for award in item.awards:
        if award.strip():
            lines.append(f"奖项：{award.strip()}")
    for section in item.custom_sections:
        if section.title.strip():
            lines.append(f"补充：{section.title.strip()}")
    return "\n".join(lines).strip()


def _build_resume_preview(segment_key: str, resume_data: ResumeStructuredData) -> str:
    builders = {
        "summary": _build_summary_text,
        "experience": _build_experience_text,
        "projects": _build_projects_text,
        "skills": _build_skills_text,
        "additional": _build_additional_text,
    }
    return builders[segment_key](resume_data)


def _reorder_skills_for_job(
    *,
    resume_data: ResumeStructuredData,
    job_keywords: list[str],
) -> ResumeStructuredData:
    reordered = resume_data.model_copy(deep=True)
    source_skills = _dedupe_strings([*resume_data.skills.technical, *resume_data.skills.tools])
    matched = [skill for skill in source_skills if any(_keyword_supported(keyword, skill) for keyword in job_keywords)]
    remaining = [skill for skill in source_skills if skill not in matched]
    reordered.skills.technical = _dedupe_strings([*matched, *remaining])
    reordered.skills.tools = []
    return reordered


def _build_segment_explanation(
    *,
    key: str,
    original_text: str,
    suggested_text: str,
    report: MatchReport,
) -> SegmentExplanation:
    gap_json = report.gap_json or {}
    matched = _dedupe_strings([str(item) for item in gap_json.get("strengths", []) if str(item).strip()])[:3]
    gaps = _dedupe_strings([str(item) for item in gap_json.get("gaps", []) if str(item).strip()])[:3]
    if original_text.strip() == suggested_text.strip():
        what = "保留原有事实表达，未做激进改写。"
    else:
        what = f"围绕 {key} 模块调整了措辞与排序，保留原始事实不变。"
    why = "优先贴合岗位高频关键词与职责重点。" if matched or gaps else "优先保证真实、可验证和可读性。"
    value = (
        f"让招聘方更快看到与岗位直接相关的证据：{', '.join(matched or gaps)}。"
        if matched or gaps
        else "让信息层级更清楚，便于 ATS 和招聘方快速读取。"
    )
    return SegmentExplanation(what=what, why=why, value=value)


def _build_segment(
    *,
    key: str,
    label: str,
    sequence: int,
    original_resume: ResumeStructuredData,
    suggested_resume: ResumeStructuredData,
    report: MatchReport,
    status: str = "success",
    error_message: str | None = None,
) -> ContentSegment:
    original_text = _build_resume_preview(key, original_resume)
    suggested_text = _build_resume_preview(key, suggested_resume)
    return ContentSegment(
        key=key,
        label=label,
        sequence=sequence,
        status=status,  # type: ignore[arg-type]
        original_text=original_text,
        suggested_text=suggested_text,
        markdown=suggested_text,
        explanation=_build_segment_explanation(
            key=key,
            original_text=original_text,
            suggested_text=suggested_text,
            report=report,
        ),
        error_message=error_message,
        generated_at=utc_now_naive(),
    )


def _select_change_type(*, before_text: str, after_text: str) -> str:
    before = _normalize_text(before_text)
    after = _normalize_text(after_text)
    if before == after:
        return "unchanged"
    if before and after and before in after:
        return "highlight"
    if before and after and len(after) < len(before):
        return "trim"
    return "rewrite"


def _build_change_evidence(*, after_text: str, report: MatchReport) -> list[str]:
    gap_json = report.gap_json or {}
    evidence: list[str] = []
    for item in [*gap_json.get("strengths", []), *gap_json.get("gaps", [])]:
        value = str(item).strip()
        if value and _keyword_supported(value, after_text):
            evidence.append(value)
    return _dedupe_strings(evidence)[:4]


def _build_change_reason(*, change_type: str, report: MatchReport, fallback: str) -> str:
    evidence = _build_change_evidence(after_text=fallback, report=report)
    if change_type == "reorder":
        return "优先把与岗位更相关的证据放在更靠前的位置。"
    if change_type == "trim":
        return "删去与目标岗位弱相关或重复的表达，保留关键信息。"
    if change_type == "highlight":
        return (
            f"在不新增事实的前提下，强化与岗位相关的证据：{', '.join(evidence)}。"
            if evidence
            else "在不新增事实的前提下，强化与岗位最相关的关键词和成果。"
        )
    if change_type == "unchanged":
        return "当前内容已经是可保留事实，本次未建议修改。"
    return "在不新增事实的前提下，调整表达以更贴近岗位职责和关键词。"


def _build_change_suggestion(*, change_type: str, section_label: str) -> str:
    if change_type == "unchanged":
        return f"{section_label} 当前无需改动，可继续保留。"
    if change_type == "highlight":
        return f"保留原事实，优先把 {section_label} 中更贴近岗位的表达前置。"
    if change_type == "trim":
        return f"保留结论与证据，精简 {section_label} 中弱相关或重复表述。"
    if change_type == "reorder":
        return f"调整 {section_label} 的顺序，让招聘方先看到最相关内容。"
    return f"改写 {section_label} 的措辞，但不要新增无法证明的事实。"


def _append_change_item(
    items: list[ContentChangeItem],
    *,
    segment_key: str,
    section_label: str,
    item_label: str,
    before_text: str,
    after_text: str,
    report: MatchReport,
    index: int,
) -> None:
    if not _normalize_text(before_text) and not _normalize_text(after_text):
        return
    change_type = _select_change_type(before_text=before_text, after_text=after_text)
    why = _build_change_reason(change_type=change_type, report=report, fallback=after_text or before_text)
    items.append(
        ContentChangeItem(
            id=f"{segment_key}_{index}",
            segment_key=segment_key,
            section_label=section_label,
            item_label=item_label,
            change_type=change_type,  # type: ignore[arg-type]
            before_text=before_text.strip(),
            after_text=after_text.strip(),
            why=why,
            suggestion=_build_change_suggestion(change_type=change_type, section_label=section_label),
            evidence=_build_change_evidence(after_text=after_text or before_text, report=report),
        )
    )


def _build_change_items(
    *,
    source_resume: ResumeStructuredData,
    projected_resume: ResumeStructuredData,
    report: MatchReport,
) -> list[ContentChangeItem]:
    items: list[ContentChangeItem] = []

    _append_change_item(
        items,
        segment_key="summary",
        section_label="职业摘要",
        item_label="摘要",
        before_text=source_resume.basic_info.summary,
        after_text=projected_resume.basic_info.summary,
        report=report,
        index=1,
    )

    for index, (before_item, after_item) in enumerate(
        zip(source_resume.work_experience_items, projected_resume.work_experience_items, strict=False),
        start=1,
    ):
        before_label = _join_non_empty([before_item.company, before_item.title]) or f"工作经历 {index}"
        before_bullets = [bullet.text.strip() for bullet in before_item.bullets if bullet.text.strip()]
        after_bullets = [bullet.text.strip() for bullet in after_item.bullets if bullet.text.strip()]
        max_count = max(len(before_bullets), len(after_bullets))
        for bullet_index in range(max_count):
            _append_change_item(
                items,
                segment_key="experience",
                section_label="工作经历",
                item_label=f"{before_label} · 要点 {bullet_index + 1}",
                before_text=before_bullets[bullet_index] if bullet_index < len(before_bullets) else "",
                after_text=after_bullets[bullet_index] if bullet_index < len(after_bullets) else "",
                report=report,
                index=index * 100 + bullet_index + 1,
            )

    for index, (before_item, after_item) in enumerate(
        zip(source_resume.project_items, projected_resume.project_items, strict=False),
        start=1,
    ):
        before_label = _join_non_empty([before_item.name, before_item.role]) or f"项目经历 {index}"
        before_bullets = [bullet.text.strip() for bullet in before_item.bullets if bullet.text.strip()]
        if before_item.summary.strip():
            before_bullets = [before_item.summary.strip(), *before_bullets]
        after_bullets = [bullet.text.strip() for bullet in after_item.bullets if bullet.text.strip()]
        if after_item.summary.strip():
            after_bullets = [after_item.summary.strip(), *after_bullets]
        max_count = max(len(before_bullets), len(after_bullets))
        for bullet_index in range(max_count):
            _append_change_item(
                items,
                segment_key="projects",
                section_label="项目经历",
                item_label=f"{before_label} · 要点 {bullet_index + 1}",
                before_text=before_bullets[bullet_index] if bullet_index < len(before_bullets) else "",
                after_text=after_bullets[bullet_index] if bullet_index < len(after_bullets) else "",
                report=report,
                index=index * 100 + bullet_index + 1,
            )

    source_skills = _dedupe_strings([*source_resume.skills.technical, *source_resume.skills.tools])
    projected_skills = _dedupe_strings([*projected_resume.skills.technical, *projected_resume.skills.tools])
    if source_skills or projected_skills:
        top_after = projected_skills[: min(5, len(projected_skills))]
        top_before = source_skills[: len(top_after)]
        if top_before != top_after:
            _append_change_item(
                items,
                segment_key="skills",
                section_label="技能聚焦",
                item_label="技能排序",
                before_text="，".join(top_before),
                after_text="，".join(top_after),
                report=report,
                index=1,
            )

    return [item for item in items if item.change_type != "unchanged"]


def _render_tailored_resume_markdown(document: TailoredResumeDocument) -> str:
    lines: list[str] = []
    name = document.basic.name.strip() or "Tailored Resume"
    lines.append(f"# {name}")
    title_line = document.basic.title.strip()
    if title_line:
        lines.append(title_line)
    contact_line = " | ".join(
        _dedupe_strings(
            [
                document.basic.email,
                document.basic.phone,
                document.basic.location,
                *document.basic.links,
            ]
        )
    )
    if contact_line:
        lines.append(contact_line)

    if document.summary.strip():
        lines.extend(["", "## Summary", document.summary.strip()])

    if document.education:
        lines.extend(["", "## Education"])
        for item in document.education:
            header = " | ".join(
                part
                for part in [
                    _normalize_text(
                        " ".join(
                            part
                            for part in [item.school, item.major, item.degree]
                            if part
                        )
                    ),
                    _normalize_text(
                        " - ".join(
                            part for part in [item.startDate, item.endDate] if part
                        )
                    ),
                ]
                if part
            )
            if header:
                lines.append(f"- {header}")
            for desc in item.description:
                if _normalize_text(desc):
                    lines.append(f"  - {_normalize_text(desc)}")

    if document.experience:
        lines.extend(["", "## Work Experience"])
        for item in document.experience:
            header = " | ".join(
                part
                for part in [
                    _normalize_text(
                        " ".join(part for part in [item.company, item.position] if part)
                    ),
                    _normalize_text(
                        " - ".join(
                            part for part in [item.startDate, item.endDate] if part
                        )
                    ),
                ]
                if part
            )
            if header:
                lines.append(f"- {header}")
            for bullet in item.bullets:
                if _normalize_text(bullet):
                    lines.append(f"  - {_normalize_text(bullet)}")

    if document.projects:
        lines.extend(["", "## Projects"])
        for item in document.projects:
            header = " | ".join(
                part
                for part in [
                    _normalize_text(
                        " ".join(part for part in [item.name, item.role] if part)
                    ),
                    _normalize_text(
                        " - ".join(
                            part for part in [item.startDate, item.endDate] if part
                        )
                    ),
                    item.link.strip(),
                ]
                if part
            )
            if header:
                lines.append(f"- {header}")
            for bullet in item.bullets:
                if _normalize_text(bullet):
                    lines.append(f"  - {_normalize_text(bullet)}")

    if document.skills:
        lines.extend(
            ["", "## Skills", f"- {', '.join(_dedupe_strings(document.skills))}"]
        )

    if document.certificates:
        lines.extend(
            [
                "",
                "## Certificates",
                *[f"- {item}" for item in document.certificates if item.strip()],
            ]
        )

    if document.languages:
        lines.extend(
            [
                "",
                "## Languages",
                *[f"- {item}" for item in document.languages if item.strip()],
            ]
        )

    if document.awards:
        lines.extend(
            [
                "",
                "## Awards",
                *[f"- {item}" for item in document.awards if item.strip()],
            ]
        )

    for section in document.customSections:
        if not section.title.strip():
            continue
        lines.extend(["", f"## {section.title.strip()}"])
        for item in section.items:
            header = " | ".join(
                part
                for part in [
                    item.title.strip(),
                    item.subtitle.strip(),
                    item.years.strip(),
                ]
                if part
            )
            if header:
                lines.append(f"- {header}")
            for desc in item.description:
                if _normalize_text(desc):
                    lines.append(f"  - {_normalize_text(desc)}")

    return "\n".join(lines).strip()


def _build_fallback_tailored_resume_document(
    *,
    source_resume: ResumeStructuredData,
    original_markdown: str,
    job: JobDescription,
    job_keywords: list[str],
) -> TailoredResumeDocument:
    document = _build_document_from_structured_resume(
        resume_data=source_resume,
        job=job,
        job_keywords=job_keywords,
        warnings=["AI 不可用，当前结果使用保守 fallback 生成。"],
    )
    document.markdown = original_markdown.strip() or _render_tailored_resume_markdown(
        document
    )
    return document


def _build_resume_ai_config(settings: Settings) -> AIProviderConfig:
    return AIProviderConfig(
        provider=settings.resume_ai_provider,
        base_url=settings.resume_ai_base_url,
        api_key=settings.resume_ai_api_key,
        model=settings.resume_ai_model,
        timeout_seconds=settings.resume_ai_timeout_seconds,
        connect_timeout_seconds=settings.resume_ai_connect_timeout_seconds,
        write_timeout_seconds=settings.resume_ai_write_timeout_seconds,
        read_timeout_seconds=settings.resume_ai_read_timeout_seconds,
        pool_timeout_seconds=settings.resume_ai_pool_timeout_seconds,
    )


def _build_rewrite_tasks(job: JobDescription, report: MatchReport) -> list[dict[str, Any]]:
    evidence_map = report.evidence_map_json or {}
    missing_items = [str(item) for item in evidence_map.get("missing_items", []) if str(item).strip()]
    tasks: list[dict[str, Any]] = [
        {
            "key": "summary-focus",
            "title": "强化摘要与岗位相关性",
            "instruction": f"围绕目标岗位 {job.title or '目标岗位'} 强化摘要的岗位贴合表达，禁止新增事实。",
            "target_section": "summary",
            "priority": 1,
            "selected": True,
        },
        {
            "key": "experience-focus",
            "title": "强化工作经历证据",
            "instruction": "优先让工作经历里的事实更贴近岗位要求，保留原公司、岗位、时间线和指标。",
            "target_section": "work_experience",
            "priority": 2,
            "selected": True,
        },
        {
            "key": "projects-focus",
            "title": "强化项目经历证据",
            "instruction": "优先让项目经历里的成果和职责更贴近岗位要求，禁止新增项目与指标。",
            "target_section": "projects",
            "priority": 3,
            "selected": True,
        },
    ]
    if missing_items:
        tasks.append(
            {
                "key": "missing-keywords",
                "title": "谨慎处理缺口词",
                "instruction": f"如果原简历已有证据，再自然吸收这些关键词：{', '.join(missing_items[:6])}",
                "target_section": "summary",
                "priority": 4,
                "selected": True,
            }
        )
    return tasks


async def _generate_rewrite_projection(
    *,
    source_resume: ResumeStructuredData,
    original_resume_markdown: str,
    job: JobDescription,
    report: MatchReport,
    settings: Settings,
) -> tuple[ResumeStructuredData, list[str]]:
    if not is_ai_configured(
        provider=settings.resume_ai_provider,
        base_url=settings.resume_ai_base_url,
        model=settings.resume_ai_model,
        api_key=settings.resume_ai_api_key,
    ):
        return source_resume.model_copy(deep=True), ["未配置简历优化 AI，当前保留原始摘要/经历/项目表达。"]

    payload = {
        "source_resume": source_resume.model_dump(mode="json"),
        "original_resume_markdown": original_resume_markdown,
        "job_snapshot": {
            "title": job.title,
            "company": job.company,
            "jd_text": job.jd_text,
        },
        "match_report_snapshot": {
            "fit_band": report.fit_band,
            "overall_score": str(report.overall_score or ""),
            "gap_json": report.gap_json or {},
            "evidence_map_json": report.evidence_map_json or {},
        },
        "rewrite_tasks": _build_rewrite_tasks(job, report),
    }
    logger.info(
        "tailored_resume.rewrite_request prompt_template=%s payload_keys=%s source_resume_empty_skeleton=%s source_resume_keys=%s job_snapshot_present=%s job_snapshot_keys=%s match_report_snapshot_present=%s match_report_snapshot_keys=%s original_resume_markdown_in_payload=%s rewrite_tasks_count=%s payload_json_len=%s",
        "tailored_resume/rewrite_only.txt",
        sorted(payload.keys()),
        not _resume_has_structured_signal(source_resume),
        sorted(payload["source_resume"].keys()),
        bool(payload["job_snapshot"]),
        sorted(payload["job_snapshot"].keys()),
        bool(payload["match_report_snapshot"]),
        sorted(payload["match_report_snapshot"].keys()),
        bool(payload["original_resume_markdown"].strip()),
        len(payload["rewrite_tasks"]),
        len(json.dumps(payload, ensure_ascii=False)),
    )
    try:
        response = await request_json_completion(
            config=_build_resume_ai_config(settings),
            instructions=get_tailored_resume_rewrite_prompt(),
            payload=payload,
            max_tokens=3200,
        )
        response_json_len = len(json.dumps(response, ensure_ascii=False))
        rewrite = _RewriteOnlyResponse.model_validate(response)
        logger.info(
            "tailored_resume.rewrite_result success=%s response_json_len=%s empty=%s fallback_used=%s unresolved_items=%s editor_notes=%s",
            True,
            response_json_len,
            response_json_len == 0,
            False,
            len(rewrite.unresolved_items),
            len(rewrite.editor_notes),
        )
    except (AIClientError, ValidationError):
        logger.warning(
            "tailored_resume.rewrite_result success=%s response_json_len=%s empty=%s fallback_used=%s reason=%s",
            False,
            0,
            True,
            True,
            "ai_error_or_validation_error",
        )
        return source_resume.model_copy(deep=True), ["局部改写 AI 返回无效结果，当前保留原始摘要/经历/项目表达。"]

    projected = source_resume.model_copy(deep=True)
    if rewrite.summary.strip():
        projected.basic_info.summary = rewrite.summary.strip()

    work_by_id = {item.id: item for item in projected.work_experience_items}
    for item in rewrite.work_experience_items:
        target = work_by_id.get(item.id)
        if target is None:
            continue
        bullet_by_id = {bullet.id: bullet for bullet in target.bullets}
        for bullet in item.bullets:
            target_bullet = bullet_by_id.get(bullet.id)
            if target_bullet is None:
                continue
            target_bullet.text = bullet.text.strip() or target_bullet.text
            target_bullet.kind = bullet.kind or target_bullet.kind
            target_bullet.metrics = _dedupe_strings(bullet.metrics) or target_bullet.metrics
            target_bullet.skills_used = _dedupe_strings(bullet.skills_used) or target_bullet.skills_used

    project_by_id = {item.id: item for item in projected.project_items}
    for item in rewrite.project_items:
        target = project_by_id.get(item.id)
        if target is None:
            continue
        bullet_by_id = {bullet.id: bullet for bullet in target.bullets}
        for bullet in item.bullets:
            target_bullet = bullet_by_id.get(bullet.id)
            if target_bullet is None:
                continue
            target_bullet.text = bullet.text.strip() or target_bullet.text
            target_bullet.kind = bullet.kind or target_bullet.kind
            target_bullet.metrics = _dedupe_strings(bullet.metrics) or target_bullet.metrics
            target_bullet.skills_used = _dedupe_strings(bullet.skills_used) or target_bullet.skills_used
        summary_parts = [bullet.text.strip() for bullet in item.bullets if bullet.text.strip()]
        if summary_parts and not target.summary.strip():
            target.summary = summary_parts[0]

    notes = _dedupe_strings(
        [
            *rewrite.editor_notes,
            *[str(item.get("reason") or "").strip() for item in rewrite.unresolved_items if isinstance(item, dict)],
        ]
    )
    return projected, notes


def _build_canonical_projection_from_document(
    document: TailoredResumeDocument,
    *,
    source_resume: ResumeStructuredData,
) -> ResumeStructuredData:
    projected = source_resume.model_copy(deep=True)
    projected.education = []
    projected.work_experience = []
    projected.projects = []
    projected.certifications = []
    projected.basic_info.name = (
        document.basic.name.strip() or source_resume.basic_info.name
    )
    projected.basic_info.email = (
        document.basic.email.strip() or source_resume.basic_info.email
    )
    projected.basic_info.phone = (
        document.basic.phone.strip() or source_resume.basic_info.phone
    )
    projected.basic_info.location = (
        document.basic.location.strip() or source_resume.basic_info.location
    )
    projected.basic_info.summary = (
        document.summary.strip() or source_resume.basic_info.summary
    )
    projected.education_items = [
        ResumeEducationItem(
            id=f"edu_{index}",
            school=item.school,
            degree=item.degree,
            major=item.major,
            start_date=item.startDate,
            end_date=item.endDate,
            honors=item.description,
            source_refs=[f"edu_{index}"],
        )
        for index, item in enumerate(document.education, start=1)
    ]
    projected.work_experience_items = [
        ResumeWorkExperienceItem(
            id=f"work_{index}",
            company=item.company,
            title=item.position,
            start_date=item.startDate,
            end_date=item.endDate,
            bullets=[
                ResumeExperienceBullet(
                    id=f"work_{index}_b{bullet_index}",
                    text=bullet,
                    source_refs=[f"work_{index}"],
                )
                for bullet_index, bullet in enumerate(item.bullets, start=1)
            ],
            source_refs=[f"work_{index}"],
        )
        for index, item in enumerate(document.experience, start=1)
    ]
    projected.project_items = [
        ResumeProjectItem(
            id=f"proj_{index}",
            name=item.name,
            role=item.role,
            start_date=item.startDate,
            end_date=item.endDate,
            summary=item.bullets[0] if item.bullets else "",
            bullets=[
                ResumeExperienceBullet(
                    id=f"proj_{index}_b{bullet_index}",
                    text=bullet,
                    source_refs=[f"proj_{index}"],
                )
                for bullet_index, bullet in enumerate(item.bullets, start=1)
            ],
            source_refs=[f"proj_{index}"],
        )
        for index, item in enumerate(document.projects, start=1)
    ]
    projected.skills.technical = _dedupe_strings(document.skills)
    projected.skills.languages = _dedupe_strings(document.languages)
    projected.certification_items = [
        ResumeCertificationItem(
            id=f"cert_{index}",
            name=item,
            source_refs=[f"cert_{index}"],
        )
        for index, item in enumerate(document.certificates, start=1)
    ]
    return ResumeStructuredData.model_validate(projected.model_dump())


def _infer_changed_sections(
    *,
    source_resume: ResumeStructuredData,
    projected_resume: ResumeStructuredData,
) -> list[str]:
    changed: list[str] = []
    if _normalize_text(source_resume.basic_info.summary) != _normalize_text(
        projected_resume.basic_info.summary
    ):
        changed.append("summary")
    if [_normalize_text(item) for item in source_resume.work_experience] != [
        _normalize_text(item) for item in projected_resume.work_experience
    ]:
        changed.append("experience")
    if [_normalize_text(item) for item in source_resume.projects] != [
        _normalize_text(item) for item in projected_resume.projects
    ]:
        changed.append("projects")
    if [_normalize_text(item) for item in source_resume.education] != [
        _normalize_text(item) for item in projected_resume.education
    ]:
        changed.append("education")
    if _dedupe_strings(source_resume.certifications) != _dedupe_strings(
        projected_resume.certifications
    ):
        changed.append("certificates")
    return changed


def _derive_changed_sections_from_change_items(items: list[ContentChangeItem]) -> list[str]:
    return _dedupe_strings(
        [item.segment_key for item in items if item.change_type != "unchanged"]
    )


def _finalize_document(
    *,
    document: TailoredResumeDocument,
    source_resume: ResumeStructuredData,
    original_markdown: str,
    job: JobDescription,
    job_keywords: list[str],
) -> tuple[TailoredResumeDocument, ResumeStructuredData, dict[str, Any]]:
    evidence_text = "\n".join(
        [
            original_markdown,
            *_flatten_string_values(source_resume.model_dump()),
        ]
    )
    supported_keywords = [
        keyword
        for keyword in job_keywords
        if _keyword_supported(keyword, evidence_text)
    ]
    unsupported_keywords = [
        keyword for keyword in job_keywords if keyword not in supported_keywords
    ]

    document.matchSummary.targetRole = (
        document.matchSummary.targetRole.strip() or job.title or ""
    )
    document.matchSummary.optimizationLevel = "conservative"
    document.matchSummary.matchedKeywords = _dedupe_strings(
        [
            keyword
            for keyword in document.matchSummary.matchedKeywords
            if keyword in supported_keywords
        ]
        or supported_keywords[:8]
    )
    document.matchSummary.missingButImportantKeywords = _dedupe_strings(
        [
            keyword
            for keyword in document.matchSummary.missingButImportantKeywords
            if keyword in unsupported_keywords
        ]
        or unsupported_keywords[:8]
    )
    if not document.matchSummary.overallStrategy.strip():
        document.matchSummary.overallStrategy = (
            "保留原始事实与主要模块，仅在有证据支撑处强化与目标岗位相关的表达。"
        )

    if not document.basic.title.strip():
        document.basic.title = job.title or ""

    projected_resume = _build_canonical_projection_from_document(
        document, source_resume=source_resume
    )
    fact_check_report = build_resume_fact_check_report(
        original_resume=source_resume,
        optimized_resume=projected_resume,
    )
    warnings = _dedupe_strings(
        [
            *document.audit.warnings,
            *[
                str(item.get("message") or "").strip()
                for item in fact_check_report.get("findings", [])
                if isinstance(item, dict) and str(item.get("message") or "").strip()
            ],
        ]
    )
    document.audit.truthfulnessStatus = "warning" if warnings else "passed"
    document.audit.warnings = warnings
    document.audit.changedSections = _dedupe_strings(
        [
            *document.audit.changedSections,
            *_infer_changed_sections(
                source_resume=source_resume, projected_resume=projected_resume
            ),
        ]
    )
    document.audit.addedKeywordsOnlyFromEvidence = not any(
        isinstance(item, dict)
        and str(item.get("type") or "").strip()
        in {"new_skill", "new_company", "new_project", "new_number"}
        for item in fact_check_report.get("findings", [])
    )

    if not document.markdown.strip():
        document.markdown = _render_tailored_resume_markdown(document)

    return document, projected_resume, fact_check_report


def _build_downloadable_file_name(
    *,
    session_record: ResumeOptimizationSession,
    document: TailoredResumeDocument,
) -> str:
    base_name = document.basic.name.strip() or "resume"
    safe_name = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", base_name).strip("_")
    if not safe_name:
        safe_name = "resume"
    return f"{safe_name}_tailored_{str(session_record.id)[:8]}.md"


def _resolve_tailored_resume_display_status(
    *,
    session_status: str,
    task_state: TaskState,
    segments: list[ContentSegment],
    has_markdown: bool,
) -> TailoredResumeDisplayStatus:
    normalized_session_status = _normalize_session_status(session_status)
    normalized_task_status = _normalize_task_state_status(task_state.status)

    for status in (normalized_task_status, normalized_session_status):
        if status in {"cancelled", "returned", "aborted"}:
            return status

    if normalized_task_status == "processing" or normalized_session_status == "processing":
        has_segment_progress = any(
            segment.status in {"processing", "success"} for segment in segments
        )
        return "segment_progress" if has_segment_progress else "processing"

    if normalized_task_status in {"success", "ready"} or normalized_session_status in {"success", "ready"}:
        return "success" if has_markdown else "empty_result"

    if normalized_task_status == "failed" or normalized_session_status == "failed":
        return "failed"

    return "idle"


def _build_runtime_error_message(raw_error: str | None) -> str:
    normalized = _normalize_text(raw_error or "")
    lowered = normalized.lower()
    if not normalized:
        return "优化简历生成失败，请重试。"
    if any(token in lowered for token in {"auth", "permission", "403", "401"}):
        return "优化简历服务当前鉴权失败，请稍后重试。"
    if any(token in lowered for token in {"timeout", "connection", "provider error", "http_5"}):
        return "优化简历服务暂时不可用，请稍后重试。"
    if any(token in lowered for token in {"invalid response format", "json", "validation"}):
        return "生成结果格式无效，本次任务已终止，请重试。"
    return normalized if len(normalized) <= 240 else "优化简历生成失败，请重试。"


def _extract_tailored_resume_error_message(
    *,
    session_record: ResumeOptimizationSession,
    task_state: TaskState,
    display_status: TailoredResumeDisplayStatus,
) -> str | None:
    if display_status == "empty_result":
        return "生成流程已结束，但未产出可下载的优化简历内容。"
    if display_status in {"cancelled", "returned", "aborted"}:
        return task_state.message or "本次生成任务未正常完成。"
    if display_status != "failed":
        return None

    audit_payload = session_record.audit_report_json or {}
    metrics = task_state.metrics or {}
    raw_error = (
        str(audit_payload.get("error_message") or "").strip()
        or str(audit_payload.get("error") or "").strip()
        or str(metrics.get("failure_reason") or "").strip()
        or task_state.message
    )
    return _build_runtime_error_message(raw_error)


async def _generate_tailored_resume_document(
    *,
    resume: Resume,
    job: JobDescription,
    report: MatchReport,
    payload: TailoredResumeGenerateRequest,
    settings: Settings,
) -> tuple[TailoredResumeDocument, ResumeStructuredData, dict[str, Any]]:
    source_resume = ResumeStructuredData.model_validate(resume.structured_json or {})
    original_markdown = _extract_original_resume_markdown(resume)
    job_keywords = _extract_job_keywords(job, report)
    provider = build_tailored_resume_document_ai_provider(settings)
    fallback_document = _build_fallback_tailored_resume_document(
        source_resume=source_resume,
        original_markdown=original_markdown,
        job=job,
        job_keywords=job_keywords,
    )

    try:
        ai_result = await provider.generate(
            AITailoredResumeDocumentRequest(
                output_language=source_resume.meta.language or "zh-CN",
                job_description=job.jd_text,
                job_keywords=job_keywords,
                original_resume_json=source_resume.model_dump(),
                original_resume_markdown=original_markdown,
                optimization_level=payload.optimization_level,
            )
        )
        candidate_document = ai_result.payload or fallback_document
    except AIClientError:
        candidate_document = fallback_document

    return _finalize_document(
        document=candidate_document,
        source_resume=source_resume,
        original_markdown=original_markdown,
        job=job,
        job_keywords=job_keywords,
    )


def _build_tailored_resume_artifact(
    *,
    session_record: ResumeOptimizationSession,
    report: MatchReport,
) -> TailoredResumeArtifactResponse:
    try:
        document = TailoredResumeDocument.model_validate(session_record.tailored_resume_json or {})
    except ValidationError:
        document = TailoredResumeDocument()
    markdown = session_record.tailored_resume_md or document.markdown
    if markdown and markdown != document.markdown:
        document.markdown = markdown
    task_state = _deserialize_task_state(session_record.diagnosis_json)
    segments = _deserialize_segments(session_record.draft_sections_json)
    audit_payload = session_record.audit_report_json or {}
    change_items_payload = audit_payload.get("change_items") or []
    change_items: list[ContentChangeItem] = []
    if isinstance(change_items_payload, list):
        for value in change_items_payload:
            if not isinstance(value, dict):
                continue
            try:
                change_items.append(ContentChangeItem.model_validate(value))
            except ValidationError:
                continue
    has_markdown = bool(markdown.strip())
    display_status = _resolve_tailored_resume_display_status(
        session_status=session_record.status,
        task_state=task_state,
        segments=segments,
        has_markdown=has_markdown,
    )
    error_message = _extract_tailored_resume_error_message(
        session_record=session_record,
        task_state=task_state,
        display_status=display_status,
    )
    downloadable = display_status == "success" and has_markdown
    return TailoredResumeArtifactResponse(
        session_id=session_record.id,
        match_report_id=report.id,
        status=session_record.status,
        display_status=display_status,
        fit_band=report.fit_band,
        overall_score=report.overall_score or Decimal("0"),
        task_state=task_state,
        segments=segments,
        change_items=change_items,
        document=document,
        error_message=error_message,
        retryable=display_status in RETRYABLE_DISPLAY_STATUSES,
        downloadable=downloadable,
        result_is_empty=display_status == "empty_result",
        has_downloadable_markdown=downloadable,
        downloadable_file_name=(
            _build_downloadable_file_name(
                session_record=session_record,
                document=document,
            )
            if downloadable
            else None
        ),
        created_at=session_record.created_at,
        updated_at=session_record.updated_at,
    )


async def _build_workflow_response(
    session: AsyncSession,
    *,
    current_user: User,
    session_record: ResumeOptimizationSession,
    report: MatchReport,
) -> TailoredResumeWorkflowResponse:
    job = await get_job_or_404(
        session, current_user=current_user, job_id=session_record.jd_id
    )
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
    return TailoredResumeWorkflowResponse(
        resume=resume_payload,
        target_job=job_payload,
        tailored_resume=_build_tailored_resume_artifact(
            session_record=session_record,
            report=report,
        ),
    )


def _ensure_resume_ready_for_tailoring(
    *,
    parse_status: str,
    has_resume_markdown: bool,
    structured_payload: dict[str, Any] | None,
) -> None:
    structured_resume, structured_reason = _validate_structured_resume_payload(
        structured_payload
    )
    if parse_status == "success" and has_resume_markdown and structured_resume is not None:
        logger.info(
            "tailored_resume.resume_gate_passed parse_status=%s has_resume_markdown=%s rule=parse_success_and_markdown_and_structured structured_json_checked=%s structured_reason=%s structured_keys=%s",
            parse_status,
            has_resume_markdown,
            True,
            "ready",
            _structured_top_level_keys(structured_payload),
        )
        return
    logger.warning(
        "tailored_resume.resume_gate_failed parse_status=%s has_resume_markdown=%s rule=parse_success_and_markdown_and_structured structured_json_checked=%s structured_reason=%s structured_keys=%s",
        parse_status,
        has_resume_markdown,
        True,
        structured_reason,
        _structured_top_level_keys(structured_payload),
    )
    if parse_status != "success" or not has_resume_markdown:
        message = "主简历尚未完成 Markdown 解析，暂时不能生成定制简历。"
    elif structured_reason in {"missing", "empty"}:
        message = "主简历已完成 Markdown 解析，但尚未完成结构化。请先保存主简历，生成结构化内容后再生成定制简历。"
    else:
        message = "主简历的结构化内容无效。请重新保存主简历后再生成定制简历。"
    raise ApiException(
        status_code=409,
        code=ErrorCode.CONFLICT,
        message=message,
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
    message = (
        report.error_message or "Match report generation did not finish successfully"
    )
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


def _build_initial_segments() -> list[ContentSegment]:
    return [
        ContentSegment(key=key, label=label, sequence=index, status="pending")
        for index, (key, label) in enumerate(TAILORED_RESUME_SEGMENT_ORDER, start=1)
    ]


def _reset_failed_segments(existing: list[ContentSegment]) -> list[ContentSegment]:
    normalized: list[ContentSegment] = []
    existing_by_key = {segment.key: segment for segment in existing}
    for index, (key, label) in enumerate(TAILORED_RESUME_SEGMENT_ORDER, start=1):
        segment = existing_by_key.get(key) or ContentSegment(
            key=key,
            label=label,
            sequence=index,
            status="pending",
        )
        if segment.status == "failed":
            segment.status = "pending"
            segment.error_message = None
        normalized.append(segment)
    return normalized


def _prepare_session_for_tailored_generation(
    session_record: ResumeOptimizationSession,
    *,
    preserve_segments: bool,
) -> None:
    existing_segments = _deserialize_segments(session_record.draft_sections_json)
    segments = _reset_failed_segments(existing_segments) if preserve_segments else _build_initial_segments()
    session_record.status = "processing"
    session_record.tailored_resume_json = {}
    session_record.tailored_resume_md = ""
    session_record.optimized_resume_md = ""
    session_record.audit_report_json = {}
    session_record.draft_sections_json = _serialize_segments(segments)
    state = TaskState(
        status="processing",
        phase="queued",
        message="已创建任务，准备按段生成专属简历。",
        current_step=sum(1 for segment in segments if segment.status == "success"),
        total_steps=len(TAILORED_RESUME_SEGMENT_ORDER),
        started_at=utc_now_naive(),
        last_updated_at=utc_now_naive(),
        metrics={},
    )
    session_record.diagnosis_json = state.model_dump(mode="json")
    _append_event(session_record.diagnosis_json, event_type="tailored_resume_started")


async def retry_tailored_resume_workflow(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> ResumeOptimizationSession:
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
    _prepare_session_for_tailored_generation(
        session_record,
        preserve_segments=True,
    )
    session_record.updated_by = current_user.id
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return session_record


async def record_tailored_resume_event(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
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
    diagnosis = dict(session_record.diagnosis_json or {})
    _append_event(diagnosis, event_type=event_type, payload=payload)
    session_record.diagnosis_json = diagnosis
    session.add(session_record)
    await session.commit()


async def process_tailored_resume_workflow(
    *,
    session_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    async with session_factory() as session:
        session_record = await session.get(ResumeOptimizationSession, session_id)
        if session_record is None:
            return
        resume = await session.get(Resume, session_record.resume_id)
        job = await session.get(JobDescription, session_record.jd_id)
        report = await session.get(MatchReport, session_record.match_report_id)
        if resume is None or job is None or report is None:
            _mark_task_state(
                session_record,
                status="failed",
                phase="failed",
                message="生成失败，所需的简历或岗位数据不存在。",
            )
            session_record.status = "failed"
            session_record.audit_report_json = {
                "error": "missing_dependencies",
                "error_message": "生成失败，所需的简历或岗位数据不存在。",
            }
            session.add(session_record)
            await session.commit()
            return

        try:
            if report.status == "pending":
                _mark_task_state(
                    session_record,
                    status="processing",
                    phase="preparing_match_report",
                    message="正在准备岗位匹配结果。",
                    total_steps=len(TAILORED_RESUME_SEGMENT_ORDER),
                )
                session.add(session_record)
                await session.commit()
                await process_match_report(
                    report_id=report.id,
                    session_factory=session_factory,
                    settings=settings,
                )
                await session.refresh(session_record)
                report = await session.get(MatchReport, session_record.match_report_id)
                if report is None:
                    raise RuntimeError("Tailored resume match report disappeared after processing")

            resume_snapshot = _resume_input_snapshot(resume)
            logger.info(
                "tailored_resume.workflow_start session_id=%s resume_id=%s job_id=%s parse_status=%s structured_json_empty=%s structured_json_keys=%s canonical_resume_md_present=%s canonical_resume_md_len=%s raw_text_present=%s raw_text_len=%s",
                session_id,
                resume.id,
                job.id,
                resume_snapshot["parse_status"],
                resume_snapshot["structured_json_empty"],
                resume_snapshot["structured_json_keys"],
                resume_snapshot["canonical_resume_md_present"],
                resume_snapshot["canonical_resume_md_len"],
                resume_snapshot["raw_text_present"],
                resume_snapshot["raw_text_len"],
            )
            source_resume = ResumeStructuredData.model_validate(resume.structured_json or {})
            original_markdown = _extract_original_resume_markdown(resume)
            job_keywords = _extract_job_keywords(job, report)
            logger.info(
                "tailored_resume.workflow_inputs_ready session_id=%s resume_id=%s job_id=%s source_resume_empty_skeleton=%s source_resume_keys=%s original_resume_markdown_len=%s job_keywords_count=%s match_report_status=%s",
                session_id,
                resume.id,
                job.id,
                not _resume_has_structured_signal(source_resume),
                _structured_top_level_keys(source_resume.model_dump(mode="json")),
                len(original_markdown),
                len(job_keywords),
                report.status,
            )

            skills_resume = _reorder_skills_for_job(
                resume_data=source_resume,
                job_keywords=job_keywords,
            )
            skills_segment = _build_segment(
                key="skills",
                label="技能聚焦",
                sequence=2,
                original_resume=source_resume,
                suggested_resume=skills_resume,
                report=report,
            )
            _store_segment(session_record, segment=skills_segment)
            state = _mark_task_state(
                session_record,
                status="processing",
                phase="optimizing_skills",
                message="正在整理更贴近岗位的技能呈现。",
                current_step=1,
                total_steps=len(TAILORED_RESUME_SEGMENT_ORDER),
            )
            if state.first_completed_at is None:
                state.first_completed_at = utc_now_naive()
            state.metrics["first_segment_latency_ms"] = int(
                max(
                    0,
                    (
                        state.first_completed_at - (state.started_at or state.first_completed_at)
                    ).total_seconds()
                    * 1000,
                )
            )
            session_record.diagnosis_json = state.model_dump(mode="json")
            session.add(session_record)
            await session.commit()

            additional_segment = _build_segment(
                key="additional",
                label="教育与补充信息",
                sequence=5,
                original_resume=source_resume,
                suggested_resume=skills_resume,
                report=report,
            )
            _store_segment(session_record, segment=additional_segment)
            _mark_task_state(
                session_record,
                status="processing",
                phase="optimizing_core_sections",
                message="正在优化摘要、工作经历和项目经历。",
                current_step=2,
                total_steps=len(TAILORED_RESUME_SEGMENT_ORDER),
            )
            session.add(session_record)
            await session.commit()

            projected_resume, notes = await _generate_rewrite_projection(
                source_resume=skills_resume,
                original_resume_markdown=original_markdown,
                job=job,
                report=report,
                settings=settings,
            )

            for sequence, (key, label) in enumerate(TAILORED_RESUME_SEGMENT_ORDER[:1] + TAILORED_RESUME_SEGMENT_ORDER[2:4], start=1):
                suggested_resume = projected_resume
                if key == "summary":
                    segment = _build_segment(
                        key=key,
                        label=label,
                        sequence=1,
                        original_resume=source_resume,
                        suggested_resume=suggested_resume,
                        report=report,
                    )
                elif key == "experience":
                    segment = _build_segment(
                        key=key,
                        label=label,
                        sequence=3,
                        original_resume=source_resume,
                        suggested_resume=suggested_resume,
                        report=report,
                    )
                else:
                    segment = _build_segment(
                        key=key,
                        label=label,
                        sequence=4,
                        original_resume=source_resume,
                        suggested_resume=suggested_resume,
                        report=report,
                    )
                _store_segment(session_record, segment=segment)
                completed_count = sum(
                    1
                    for item in _deserialize_segments(session_record.draft_sections_json)
                    if item.status == "success"
                )
                _mark_task_state(
                    session_record,
                    status="processing",
                    phase=f"optimizing_{key}",
                    message=f"正在完成{label}。",
                    current_step=completed_count,
                    total_steps=len(TAILORED_RESUME_SEGMENT_ORDER),
                )
                session.add(session_record)
                await session.commit()

            document = _build_document_from_structured_resume(
                resume_data=projected_resume,
                job=job,
                job_keywords=job_keywords,
                warnings=notes,
            )
            document.markdown = _render_tailored_resume_markdown(document)
            document, canonical_projection, fact_check_report = _finalize_document(
                document=document,
                source_resume=source_resume,
                original_markdown=original_markdown,
                job=job,
                job_keywords=job_keywords,
            )
            change_items = _build_change_items(
                source_resume=source_resume,
                projected_resume=canonical_projection,
                report=report,
            )
            document.audit.changedSections = _derive_changed_sections_from_change_items(
                change_items
            )
            if not change_items and document.audit.warnings:
                document.audit.warnings = _dedupe_strings(
                    [
                        "本次未建议修改，原因是输入内容缺少足够的可安全改写事实或岗位相关证据。",
                        *document.audit.warnings,
                    ]
                )
            session_record.optimized_resume_json = canonical_projection.model_dump()
            session_record.optimized_resume_md = document.markdown
            session_record.tailored_resume_json = document.model_dump(mode="json")
            session_record.tailored_resume_md = document.markdown
            session_record.audit_report_json = {
                "document_audit": document.audit.model_dump(mode="json"),
                "fact_check_report": fact_check_report,
                "editor_notes": notes,
                "change_items": [item.model_dump(mode="json") for item in change_items],
            }
            session_record.status = "success"
            completion_message = (
                "专属简历已按分段生成完成。"
                if document.markdown.strip()
                else "生成流程已完成，但未产出可下载的优化简历内容。"
            )
            final_state = _mark_task_state(
                session_record,
                status="success",
                phase="completed",
                message=completion_message,
                current_step=len(TAILORED_RESUME_SEGMENT_ORDER),
                total_steps=len(TAILORED_RESUME_SEGMENT_ORDER),
            )
            final_state.metrics["total_duration_ms"] = int(
                max(
                    0,
                    (
                        (final_state.completed_at or utc_now_naive()) - (final_state.started_at or utc_now_naive())
                    ).total_seconds()
                    * 1000,
                )
            )
            session_record.diagnosis_json = final_state.model_dump(mode="json")
            _append_event(session_record.diagnosis_json, event_type="tailored_resume_completed")
            logger.info(
                "tailored_resume.workflow_completed session_id=%s resume_id=%s job_id=%s markdown_len=%s change_items=%s warnings=%s",
                session_id,
                resume.id,
                job.id,
                len(document.markdown or ""),
                len(change_items),
                len(document.audit.warnings),
            )
            session.add(session_record)
            await session.commit()
        except Exception as exc:
            raw_error = str(exc)
            user_error_message = _build_runtime_error_message(raw_error)
            logger.exception(
                "Tailored resume workflow failed session_id=%s",
                session_id,
                exc_info=exc,
            )
            failure_state = _mark_task_state(
                session_record,
                status="failed",
                phase="failed",
                message=user_error_message,
            )
            failure_state.metrics["failure_reason"] = raw_error
            session_record.diagnosis_json = failure_state.model_dump(mode="json")
            session_record.status = "failed"
            session_record.audit_report_json = {
                **(session_record.audit_report_json or {}),
                "error": raw_error,
                "error_message": user_error_message,
            }
            _append_event(
                session_record.diagnosis_json,
                event_type="tailored_resume_failed",
                payload={"message": raw_error},
            )
            session.add(session_record)
            await session.commit()


async def generate_tailored_resume_workflow(
    session: AsyncSession,
    *,
    current_user: User,
    payload: TailoredResumeGenerateRequest,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> TailoredResumeWorkflowResponse:
    current_user_id = _resolve_user_id(current_user)
    current_user = await session.get(User, current_user_id)
    if current_user is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Current user not found",
        )
    resume = await get_resume_for_user(
        session,
        current_user=current_user,
        resume_id=payload.resume_id,
    )
    resume_id = resume.id
    original_markdown = _extract_original_resume_markdown(resume)
    _ensure_resume_ready_for_tailoring(
        parse_status=resume.parse_status,
        has_resume_markdown=bool(original_markdown.strip()),
        structured_payload=resume.structured_json if isinstance(resume.structured_json, dict) else None,
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
    current_user = await session.get(User, current_user_id)
    if current_user is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Current user not found",
        )
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
        current_user = await session.get(User, current_user_id)
        if current_user is None:
            raise ApiException(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message="Current user not found",
            )
        report = await get_match_report_or_404(
            session,
            current_user=current_user,
            report_id=report_id,
        )
    _ensure_match_report_ready(report)

    current_user = await session.get(User, current_user_id)
    if current_user is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Current user not found",
        )
    session_record, _resume, job, report = await create_resume_optimization_session(
        session,
        current_user=current_user,
        payload=ResumeOptimizationSessionCreateRequest(match_report_id=report.id),
    )
    session_record_id = session_record.id
    session_id = session_record.id

    should_regenerate = (
        payload.force_refresh
        or not session_record.tailored_resume_md.strip()
        or not session_record.tailored_resume_json
    )
    if should_regenerate:
        _prepare_session_for_tailored_generation(
            session_record,
            preserve_segments=False,
        )
        session_record.updated_by = current_user_id
        session.add(session_record)
        await session.commit()
        await session.refresh(session_record)
        session_id = session_record.id

    session.expire_all()
    current_user = await session.get(User, current_user_id)
    if current_user is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Current user not found",
        )
    return await get_tailored_resume_workflow(
        session,
        current_user=current_user,
        session_id=session_id,
    )


async def generate_tailored_resume_for_saved_job(
    session: AsyncSession,
    *,
    current_user: User,
    payload: TailoredResumeGenerateFromSavedJobRequest,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> TailoredResumeWorkflowResponse:
    current_user_id = _resolve_user_id(current_user)
    current_user = await session.get(User, current_user_id)
    if current_user is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Current user not found",
        )

    resume = await get_resume_for_user(
        session,
        current_user=current_user,
        resume_id=payload.resume_id,
    )
    original_markdown = _extract_original_resume_markdown(resume)
    _ensure_resume_ready_for_tailoring(
        parse_status=resume.parse_status,
        has_resume_markdown=bool(original_markdown.strip()),
        structured_payload=resume.structured_json if isinstance(resume.structured_json, dict) else None,
    )

    job = await get_job_or_404(
        session,
        current_user=current_user,
        job_id=payload.job_id,
    )
    _ensure_job_ready_for_tailoring(job)

    report = await create_match_report(
        session,
        current_user=current_user,
        job_id=job.id,
        payload=MatchReportCreateRequest(
            resume_id=resume.id,
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
        current_user = await session.get(User, current_user_id)
        if current_user is None:
            raise ApiException(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message="Current user not found",
            )
        report = await get_match_report_or_404(
            session,
            current_user=current_user,
            report_id=report_id,
        )
        resume = await get_resume_for_user(
            session,
            current_user=current_user,
            resume_id=payload.resume_id,
        )
        job = await get_job_or_404(
            session,
            current_user=current_user,
            job_id=payload.job_id,
        )
    _ensure_match_report_ready(report)

    session_record, _resume, job, report = await create_resume_optimization_session(
        session,
        current_user=current_user,
        payload=ResumeOptimizationSessionCreateRequest(match_report_id=report.id),
    )
    session_record_id = session_record.id

    should_regenerate = (
        payload.force_refresh
        or not session_record.tailored_resume_md.strip()
        or not session_record.tailored_resume_json
    )
    if should_regenerate:
        _prepare_session_for_tailored_generation(
            session_record,
            preserve_segments=False,
        )
        session_record.updated_by = current_user_id
        session.add(session_record)
        await session.commit()
        await session.refresh(session_record)

    session.expire_all()
    current_user = await session.get(User, current_user_id)
    if current_user is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Current user not found",
        )
    return await get_tailored_resume_workflow(
        session,
        current_user=current_user,
        session_id=session_record_id,
    )
