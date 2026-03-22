from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

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
    TailoredResumeEducationItem,
    TailoredResumeExperienceItem,
    TailoredResumeGenerateRequest,
    TailoredResumeGenerateFromSavedJobRequest,
    TailoredResumeMatchSummary,
    TailoredResumeProjectItem,
    TailoredResumeWorkflowResponse,
)
from app.services.ai_client import AIClientError
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
from app.services.tailored_resume_document_ai import (
    AITailoredResumeDocumentRequest,
    build_tailored_resume_document_ai_provider,
)

TOKEN_PATTERN = re.compile(r"[a-z0-9+#./-]+|[\u4e00-\u9fff]+", re.IGNORECASE)


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
    evidence_text = "\n".join(
        [
            original_markdown,
            *_flatten_string_values(source_resume.model_dump()),
        ]
    )
    matched_keywords = [
        keyword
        for keyword in job_keywords
        if _keyword_supported(keyword, evidence_text)
    ]
    missing_keywords = [
        keyword for keyword in job_keywords if keyword not in matched_keywords
    ]

    document = TailoredResumeDocument(
        matchSummary=TailoredResumeMatchSummary(
            targetRole=job.title or "",
            optimizationLevel="conservative",
            matchedKeywords=matched_keywords[:8],
            missingButImportantKeywords=missing_keywords[:8],
            overallStrategy="在不新增事实的前提下，保留原简历主体内容，并优先强化与目标岗位直接相关的表达。",
        ),
        basic=TailoredResumeBasic(
            name=source_resume.basic_info.name,
            title=job.title or source_resume.basic_info.summary,
            email=source_resume.basic_info.email,
            phone=source_resume.basic_info.phone,
            location=source_resume.basic_info.location,
            links=[],
        ),
        summary=source_resume.basic_info.summary,
        education=[
            TailoredResumeEducationItem(
                school=item.school,
                major=item.major,
                degree=item.degree,
                startDate=item.start_date,
                endDate=item.end_date,
                description=_dedupe_strings(item.honors),
            )
            for item in source_resume.education_items
        ],
        experience=[
            TailoredResumeExperienceItem(
                company=item.company,
                position=item.title,
                startDate=item.start_date,
                endDate=item.end_date,
                bullets=[bullet.text for bullet in item.bullets if bullet.text.strip()],
            )
            for item in source_resume.work_experience_items
        ],
        projects=[
            TailoredResumeProjectItem(
                name=item.name,
                role=item.role,
                startDate=item.start_date,
                endDate=item.end_date,
                bullets=_dedupe_strings(
                    [
                        item.summary,
                        *[
                            bullet.text
                            for bullet in item.bullets
                            if bullet.text.strip()
                        ],
                    ]
                ),
                link="",
            )
            for item in source_resume.project_items
        ],
        skills=_dedupe_strings(
            [*source_resume.skills.technical, *source_resume.skills.tools]
        ),
        certificates=_dedupe_strings(source_resume.certifications),
        languages=_dedupe_strings(source_resume.skills.languages),
        awards=[],
        customSections=[],
        audit=TailoredResumeAudit(
            truthfulnessStatus="warning",
            warnings=["AI 不可用，当前结果使用保守 fallback 生成。"],
            changedSections=[],
            addedKeywordsOnlyFromEvidence=True,
        ),
    )
    document.markdown = original_markdown.strip() or _render_tailored_resume_markdown(
        document
    )
    return document


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
    document = TailoredResumeDocument.model_validate(
        session_record.tailored_resume_json or {}
    )
    markdown = session_record.tailored_resume_md or document.markdown
    if markdown and markdown != document.markdown:
        document.markdown = markdown
    return TailoredResumeArtifactResponse(
        session_id=session_record.id,
        match_report_id=report.id,
        status=session_record.status,
        fit_band=report.fit_band,
        overall_score=report.overall_score or Decimal("0"),
        document=document,
        has_downloadable_markdown=bool(markdown.strip()),
        downloadable_file_name=(
            _build_downloadable_file_name(
                session_record=session_record,
                document=document,
            )
            if markdown.strip()
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
    *, parse_status: str, has_resume_markdown: bool
) -> None:
    if parse_status == "success" and has_resume_markdown:
        return
    raise ApiException(
        status_code=409,
        code=ErrorCode.CONFLICT,
        message="Resume must be parsed successfully into markdown before generating a tailored resume",
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
        if (
            not session_record.tailored_resume_json
            and not session_record.tailored_resume_md.strip()
        ):
            continue
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
        document, canonical_projection, fact_check_report = (
            await _generate_tailored_resume_document(
                resume=resume,
                job=job,
                report=report,
                payload=payload,
                settings=settings,
            )
        )
        # Legacy compatibility projection only; canonical facts are not updated in this workflow.
        session_record.optimized_resume_json = canonical_projection.model_dump()
        session_record.optimized_resume_md = document.markdown
        session_record.tailored_resume_json = document.model_dump()
        session_record.tailored_resume_md = document.markdown
        session_record.audit_report_json = {
            "document_audit": document.audit.model_dump(),
            "fact_check_report": fact_check_report,
        }
        session_record.status = "ready"
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
        document, canonical_projection, fact_check_report = (
            await _generate_tailored_resume_document(
                resume=resume,
                job=job,
                report=report,
                payload=TailoredResumeGenerateRequest(
                    resume_id=resume.id,
                    job_id=job.id,
                    title=job.title,
                    company=job.company,
                    job_city=job.job_city,
                    employment_type=job.employment_type,
                    source_name=job.source_name,
                    source_url=job.source_url,
                    priority=job.priority,
                    jd_text=job.jd_text,
                    force_refresh=payload.force_refresh,
                    optimization_level=payload.optimization_level,
                ),
                settings=settings,
            )
        )
        session_record.optimized_resume_json = canonical_projection.model_dump()
        session_record.optimized_resume_md = document.markdown
        session_record.tailored_resume_json = document.model_dump()
        session_record.tailored_resume_md = document.markdown
        session_record.audit_report_json = {
            "document_audit": document.audit.model_dump(),
            "fact_check_report": fact_check_report,
        }
        session_record.status = "ready"
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
