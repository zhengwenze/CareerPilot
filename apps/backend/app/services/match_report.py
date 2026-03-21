from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.models import JobDescription, JobReadinessEvent, MatchReport, Resume, User
from app.schemas.job import JobStructuredData
from app.schemas.match_report import (
    MatchReportCreateRequest,
    MatchReportDeleteResponse,
    MatchReportResponse,
)
from app.schemas.resume import ResumeStructuredData
from app.services.job import get_job_or_404
from app.services.match_ai import (
    AIMatchReportRequest,
    build_ai_match_correction_provider,
)
from app.services.match_engine import build_resume_evidence_profile, build_rule_match_result
from app.services.resume import get_resume_for_user


def serialize_match_report(report: MatchReport) -> MatchReportResponse:
    return MatchReportResponse(
        id=report.id,
        user_id=report.user_id,
        resume_id=report.resume_id,
        jd_id=report.jd_id,
        resume_version=report.resume_version,
        job_version=report.job_version,
        status=report.status,
        fit_band=report.fit_band,
        stale_status=report.stale_status,
        overall_score=report.overall_score,
        rule_score=report.rule_score,
        model_score=report.model_score,
        dimension_scores_json=report.dimension_scores_json or {},
        gap_json=report.gap_json or {},
        evidence_json=report.evidence_json or {},
        scorecard_json=report.scorecard_json or {},
        evidence_map_json=report.evidence_map_json or {},
        gap_taxonomy_json=report.gap_taxonomy_json or {},
        action_pack_json=report.action_pack_json or {},
        tailoring_plan_json=report.tailoring_plan_json or {},
        interview_blueprint_json=report.interview_blueprint_json or {},
        error_message=report.error_message,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _to_decimal_score(value: float) -> Decimal:
    return Decimal(str(round(value, 2))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _sanitize_insight_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    sanitized: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for item in items:
        label = str(item.get("label", "")).strip()
        reason = str(item.get("reason", "")).strip()
        severity = str(item.get("severity", "medium")).strip() or "medium"
        if not label or not reason:
            continue
        key = (label.lower(), reason.lower())
        if key in seen:
            continue
        seen.add(key)
        sanitized.append(
            {
                "label": label,
                "reason": reason,
                "severity": severity,
            }
        )

    return sanitized


def _sanitize_action_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    sanitized: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()

    for raw_item in items:
        title = str(raw_item.get("title", "")).strip()
        description = str(raw_item.get("description", "")).strip()
        target_section = str(
            raw_item.get("target_section", "work_experience_or_projects")
        ).strip() or "work_experience_or_projects"
        if not title or not description:
            continue
        key = (title.lower(), description.lower(), target_section.lower())
        if key in seen:
            continue
        seen.add(key)
        priority_value = raw_item.get("priority", len(sanitized) + 1)
        try:
            priority = max(1, int(priority_value))
        except (TypeError, ValueError):
            priority = len(sanitized) + 1
        sanitized.append(
            {
                "priority": priority,
                "title": title,
                "description": description,
                "target_section": target_section,
            }
        )

    sanitized.sort(key=lambda item: (int(item["priority"]), str(item["title"]).lower()))
    for index, item in enumerate(sanitized, start=1):
        item["priority"] = index
    return sanitized[:5]


def _compact_resume_snapshot(
    resume: ResumeStructuredData,
    *,
    evidence_profile: object | None = None,
) -> dict[str, object]:
    skills = [
        *resume.skills.technical[:8],
        *resume.skills.tools[:6],
        *resume.skills.languages[:4],
    ]
    profile_payload = {}
    if evidence_profile is not None:
        profile_payload = {
            "candidate_profile": {
                "skills": getattr(evidence_profile, "skills", [])[:12],
                "keywords": getattr(evidence_profile, "keywords", [])[:10],
                "estimated_years": round(float(getattr(evidence_profile, "estimated_years", 0.0)), 2),
                "education_level": getattr(evidence_profile, "education_label", None),
                "locations": getattr(evidence_profile, "locations", [])[:4],
            },
            "evidence_snippets": [
                {
                    "source_type": item.source_type,
                    "source_label": item.source_label,
                    "text": item.text,
                }
                for item in getattr(evidence_profile, "evidence_snippets", [])[:8]
            ],
        }
    return {
        "summary": resume.basic_info.summary,
        "location": resume.basic_info.location,
        "education": resume.education[:3],
        "recent_roles": resume.work_experience[:4],
        "projects": resume.projects[:4],
        "skills": skills,
        "certifications": resume.certifications[:4],
        **profile_payload,
    }


def _compact_job_snapshot(job: JobStructuredData) -> dict[str, object]:
    required_skills = [
        *job.requirements.required_skills[:8],
        *job.must_have[:4],
    ]
    preferred_skills = [
        *job.requirements.preferred_skills[:6],
        *job.nice_to_have[:4],
    ]
    keywords = [
        *job.requirements.required_keywords[:8],
        *job.domain_context.keywords[:8],
    ]
    return {
        "title": job.basic.title,
        "company": job.basic.company,
        "job_city": job.basic.job_city,
        "summary": job.raw_summary or job.domain_context.summary,
        "must_have": job.must_have[:6],
        "nice_to_have": job.nice_to_have[:6],
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "keywords": keywords,
        "experience": {
            "min_years": job.requirements.experience_min_years
            or job.experience_constraints.experience_min_years,
            "education": job.requirements.education
            or job.experience_constraints.education,
            "employment_type": job.basic.employment_type
            or job.experience_constraints.employment_type,
        },
        "responsibilities": job.responsibilities[:6],
    }


def _compact_rule_result(rule_result: object) -> dict[str, object]:
    evidence = getattr(rule_result, "evidence", {}) or {}
    evidence_map = getattr(rule_result, "evidence_map", {}) or {}
    return {
        "rule_score": getattr(rule_result, "rule_score", getattr(rule_result, "overall_score", 0.0)),
        "semantic_score": getattr(rule_result, "semantic_score", 0.0),
        "dimension_scores": getattr(rule_result, "dimension_scores", {}),
        "strengths": getattr(rule_result, "strengths", [])[:3],
        "gaps": getattr(rule_result, "gaps", [])[:3],
        "actions": getattr(rule_result, "actions", [])[:3],
        "evidence": {
            "candidate_profile": evidence.get("candidate_profile", {}),
            "matched_resume_fields": evidence_map.get("matched_resume_fields", {}),
            "matched_jd_fields": evidence_map.get("matched_jd_fields", {}),
            "missing_items": evidence_map.get("missing_items", [])[:5],
            "requirement_matches": evidence_map.get("requirement_matches", [])[:8],
            "notes": evidence_map.get("notes", [])[:3],
        },
    }


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            cleaned = str(item).strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            merged.append(cleaned)
    return merged


def _merge_dict_list_values(
    base: dict[str, object],
    overlay: dict[str, object],
) -> dict[str, list[str]]:
    keys = set(base.keys()) | set(overlay.keys())
    result: dict[str, list[str]] = {}
    for key in keys:
        base_items = base.get(key, [])
        overlay_items = overlay.get(key, [])
        if not isinstance(base_items, list):
            base_items = []
        if not isinstance(overlay_items, list):
            overlay_items = []
        result[key] = _merge_unique_strings(
            [str(item) for item in base_items],
            [str(item) for item in overlay_items],
        )
    return result


def _fit_band_from_score(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 72:
        return "strong"
    if score >= 55:
        return "partial"
    return "weak"


def _merge_candidate_profile(
    base: dict[str, object],
    overlay: dict[str, object],
) -> dict[str, object]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, list):
            current = result.get(key, [])
            if not isinstance(current, list):
                current = []
            result[key] = _merge_unique_strings(
                [str(item) for item in current],
                [str(item) for item in value],
            )
        elif value not in (None, "", []):
            result[key] = value
    return result


def _merge_evidence_map(
    *,
    base_map: dict[str, object],
    overlay_map: dict[str, object],
    resume_version: int,
    job_version: int,
) -> dict[str, object]:
    merged = {
        "matched_resume_fields": _merge_dict_list_values(
            base_map.get("matched_resume_fields", {})
            if isinstance(base_map.get("matched_resume_fields", {}), dict)
            else {},
            overlay_map.get("matched_resume_fields", {})
            if isinstance(overlay_map.get("matched_resume_fields", {}), dict)
            else {},
        ),
        "matched_jd_fields": _merge_dict_list_values(
            base_map.get("matched_jd_fields", {})
            if isinstance(base_map.get("matched_jd_fields", {}), dict)
            else {},
            overlay_map.get("matched_jd_fields", {})
            if isinstance(overlay_map.get("matched_jd_fields", {}), dict)
            else {},
        ),
        "missing_items": _merge_unique_strings(
            list(base_map.get("missing_items", []) or []),
            list(overlay_map.get("missing_items", []) or []),
        )[:10],
        "notes": _merge_unique_strings(
            list(base_map.get("notes", []) or []),
            list(overlay_map.get("notes", []) or []),
        )[:8],
        "candidate_profile": _merge_candidate_profile(
            base_map.get("candidate_profile", {})
            if isinstance(base_map.get("candidate_profile", {}), dict)
            else {},
            overlay_map.get("candidate_profile", {})
            if isinstance(overlay_map.get("candidate_profile", {}), dict)
            else {},
        ),
        "requirement_matches": base_map.get("requirement_matches", []),
        "resume_version": resume_version,
        "job_version": job_version,
    }
    return merged


def _build_missing_user_inputs(
    *,
    job_snapshot: JobStructuredData,
    resume_snapshot: ResumeStructuredData,
    missing_items: list[str],
) -> list[dict[str, str]]:
    prompts: list[dict[str, str]] = []
    if not resume_snapshot.basic_info.summary:
        prompts.append(
            {
                "field": "resume_summary",
                "question": "补充一句与你目标岗位最相关的职业摘要。",
            }
        )
    if job_snapshot.basic.job_city and not resume_snapshot.basic_info.location:
        prompts.append(
            {
                "field": "target_location",
                "question": f"确认是否接受 {job_snapshot.basic.job_city} 或远程办公。",
            }
        )
    for item in missing_items[:2]:
        prompts.append(
            {
                "field": "evidence",
                "question": f"你是否有 {item} 的项目或工作证据可补充到简历里？",
            }
        )
    return prompts[:4]


def _build_resume_tailoring_tasks(
    actions: list[dict[str, object]],
) -> list[dict[str, object]]:
    tasks: list[dict[str, object]] = []
    for action in actions[:4]:
        tasks.append(
            {
                "priority": action["priority"],
                "title": action["title"],
                "instruction": action["description"],
                "target_section": "work_experience_or_projects",
            }
        )
    return tasks


def _build_interview_focus_areas(
    *,
    gaps: list[dict[str, object]],
    strengths: list[dict[str, object]],
) -> list[dict[str, object]]:
    focus_areas: list[dict[str, object]] = []
    for item in gaps[:3]:
        focus_areas.append(
            {
                "topic": item["label"],
                "reason": item["reason"],
                "priority": "high",
            }
        )
    for item in strengths[:2]:
        focus_areas.append(
            {
                "topic": item["label"],
                "reason": "这是当前简历里最值得在面试中重点展开的优势。",
                "priority": "medium",
            }
        )
    return focus_areas[:5]


def _build_interview_blueprint(
    *,
    job_snapshot: JobStructuredData,
    fit_band: str,
    focus_areas: list[dict[str, object]],
) -> dict[str, object]:
    questions = []
    rubric = []
    for area in focus_areas[:4]:
        topic = str(area["topic"])
        questions.append(
            {
                "topic": topic,
                "question": f"请结合真实经历说明你如何体现 {topic} 能力。",
                "intent": "验证岗位关键能力是否有真实证据支撑",
            }
        )
        rubric.append(
            {
                "dimension": topic,
                "weight": 25,
                "criteria": "答案是否具体、是否有结果、是否与岗位职责直接相关",
            }
        )
    return {
        "mode": "targeted_match_mvp",
        "fit_band": fit_band,
        "target_role": job_snapshot.basic.title,
        "focus_areas": focus_areas,
        "question_pack": questions,
        "follow_up_rules": [
            "若候选人只描述职责，不描述结果，则追问指标和影响。",
            "若候选人提到技能关键词但无场景，则追问具体项目。",
        ],
        "rubric": rubric,
    }


def _build_tailoring_plan(
    *,
    job_snapshot: JobStructuredData,
    tasks: list[dict[str, object]],
    missing_items: list[str],
    missing_user_inputs: list[dict[str, str]],
) -> dict[str, object]:
    return {
        "target_summary": job_snapshot.raw_summary or job_snapshot.basic.title,
        "rewrite_tasks": tasks,
        "must_add_evidence": missing_items[:4],
        "missing_info_questions": missing_user_inputs,
    }


async def _record_job_readiness_event(
    session: AsyncSession,
    *,
    job: JobDescription,
    report: MatchReport,
    status_from: str,
    status_to: str,
    reason: str,
) -> None:
    session.add(
        JobReadinessEvent(
            user_id=job.user_id,
            job_id=job.id,
            resume_id=report.resume_id,
            match_report_id=report.id,
            status_from=status_from,
            status_to=status_to,
            reason=reason,
            metadata_json={
                "fit_band": report.fit_band,
                "stale_status": report.stale_status,
                "resume_version": report.resume_version,
                "job_version": report.job_version,
            },
            created_by=job.user_id,
            updated_by=job.user_id,
        )
    )


def _derive_job_status_stage(
    *,
    fit_band: str,
    stale_status: str,
    tailoring_task_count: int,
) -> str:
    if stale_status == "stale":
        return "matched"
    if fit_band in {"excellent", "strong"} and tailoring_task_count == 0:
        return "interview_ready"
    if tailoring_task_count > 0:
        return "tailoring_needed"
    return "matched"


async def _get_latest_report_for_pair(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
    resume_id: UUID,
) -> MatchReport | None:
    result = await session.execute(
        select(MatchReport)
        .where(
            MatchReport.user_id == current_user.id,
            MatchReport.jd_id == job_id,
            MatchReport.resume_id == resume_id,
        )
        .order_by(desc(MatchReport.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_match_report_or_404(
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


async def create_match_report(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
    payload: MatchReportCreateRequest,
) -> MatchReport:
    if not payload.force_refresh:
        reused_report = await _get_latest_report_for_pair(
            session,
            current_user=current_user,
            job_id=job_id,
            resume_id=payload.resume_id,
        )
        if reused_report is not None and reused_report.stale_status != "stale":
            return reused_report

    resume = await get_resume_for_user(
        session,
        current_user=current_user,
        resume_id=payload.resume_id,
    )
    if resume.parse_status != "success" or not resume.structured_json:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Resume must be parsed successfully before matching",
        )

    job = await get_job_or_404(session, current_user=current_user, job_id=job_id)
    if job.parse_status != "success" or not job.structured_json:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Job must be parsed successfully before matching",
        )

    report = MatchReport(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        resume_version=resume.latest_version,
        job_version=job.latest_version,
        status="pending",
        fit_band="unknown",
        stale_status="fresh",
        overall_score=_to_decimal_score(0.0),
        rule_score=_to_decimal_score(0.0),
        model_score=_to_decimal_score(0.0),
        dimension_scores_json={},
        gap_json={"strengths": [], "gaps": [], "actions": []},
        evidence_json={},
        scorecard_json={},
        evidence_map_json={},
        gap_taxonomy_json={},
        action_pack_json={},
        tailoring_plan_json={},
        interview_blueprint_json={},
        error_message=None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(report)
    await session.flush()
    job.latest_match_report_id = report.id
    job.recommended_resume_id = resume.id
    job.updated_by = current_user.id
    session.add(job)
    await session.commit()
    await session.refresh(report)
    return report


async def process_match_report(
    *,
    report_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    async with session_factory() as session:
        report = await session.get(MatchReport, report_id)
        if report is None:
            return
        report.status = "processing"
        report.error_message = None
        session.add(report)
        await session.commit()

    async with session_factory() as session:
        report = await session.get(MatchReport, report_id)
        if report is None:
            return

        resume = await session.get(Resume, report.resume_id)
        job = await session.get(JobDescription, report.jd_id)
        if resume is None or job is None:
            report.status = "failed"
            report.error_message = "Related resume or job record not found"
            session.add(report)
            await session.commit()
            return

        try:
            resume_snapshot = ResumeStructuredData.model_validate(
                resume.structured_json
            )
            job_snapshot = JobStructuredData.model_validate(job.structured_json)
            evidence_profile = build_resume_evidence_profile(
                resume=resume_snapshot,
                resume_raw_text=resume.raw_text,
            )
            rule_result = build_rule_match_result(
                resume=resume_snapshot,
                resume_raw_text=resume.raw_text,
                job=job_snapshot,
            )

            ai_payload = None
            ai_provider_name = "rule_only"
            ai_model_name = "rule_only"
            ai_status = "fallback"
            ai_reason = "AI correction did not run"

            try:
                ai_provider = build_ai_match_correction_provider(settings)
                ai_provider_name = ai_provider.provider
                ai_model_name = ai_provider.model
                ai_result = await ai_provider.correct(
                    AIMatchReportRequest(
                        resume_snapshot=_compact_resume_snapshot(
                            resume_snapshot,
                            evidence_profile=evidence_profile,
                        ),
                        job_snapshot=_compact_job_snapshot(job_snapshot),
                        rule_result=_compact_rule_result(rule_result),
                    )
                )
                ai_status = ai_result.status
                ai_reason = "AI correction applied successfully"
                if ai_result.report_payload is None:
                    raise ValueError(
                        "Match AI did not return a structured report payload"
                    )
                ai_payload = ai_result.report_payload
            except Exception as exc:
                ai_reason = str(exc)

            llm_judge_score = (
                max(0.0, min(100.0, float(ai_payload.overall_score)))
                if ai_payload is not None
                else 0.0
            )
            semantic_score = round(rule_result.semantic_score, 2)
            overall_score = round(
                (rule_result.rule_score * (0.45 if ai_payload is not None else 0.7))
                + (semantic_score * (0.20 if ai_payload is not None else 0.3))
                + (llm_judge_score * 0.35),
                2,
            )
            fit_band = _fit_band_from_score(overall_score)
            dimension_scores = {
                "rule_dimensions": dict(rule_result.dimension_scores),
                "rule_score": round(rule_result.rule_score, 2),
                "semantic_score": semantic_score,
                "llm_judge_score": round(llm_judge_score, 2),
                "composite_overall_score": overall_score,
            }
            ai_strengths = (
                [item.model_dump() for item in ai_payload.strengths]
                if ai_payload is not None
                else []
            )
            strengths = _sanitize_insight_items(
                [
                    *rule_result.strengths,
                    *ai_strengths,
                ]
            )
            should_fix = _sanitize_insight_items(
                [item.model_dump() for item in ai_payload.should_fix]
                if ai_payload is not None
                else []
            )
            ai_must_fix = (
                [item.model_dump() for item in ai_payload.must_fix]
                if ai_payload is not None
                else []
            )
            must_fix = _sanitize_insight_items(
                [
                    *rule_result.gaps,
                    *ai_must_fix,
                ]
            )
            gaps = _sanitize_insight_items([*must_fix, *should_fix])
            rewrite_tasks = (
                (
                    ai_payload.tailoring_plan_json.rewrite_tasks
                    or ai_payload.action_pack_json.resume_tailoring_tasks
                )
                if ai_payload is not None
                else []
            )
            action_candidates = [*rule_result.actions]
            action_candidates.extend(
                {
                    "priority": task.priority,
                    "title": task.title,
                    "description": task.instruction,
                    "target_section": task.target_section,
                }
                for task in rewrite_tasks
            )
            actions = _sanitize_action_items(
                action_candidates
            )
            resume_tailoring_tasks = [
                {
                    "priority": task["priority"],
                    "title": task["title"],
                    "instruction": task["description"],
                    "target_section": task["target_section"],
                }
                for task in actions
            ]
            interview_focus_areas = (
                [
                    item.model_dump()
                    for item in ai_payload.interview_blueprint_json.focus_areas
                ]
                if ai_payload is not None
                else []
            )
            if not interview_focus_areas and ai_payload is not None:
                interview_focus_areas = [
                    item.model_dump()
                    for item in ai_payload.action_pack_json.interview_focus_areas
                ]
            missing_user_inputs = (
                [
                    item.model_dump()
                    for item in ai_payload.action_pack_json.missing_user_inputs
                ]
                if ai_payload is not None
                else []
            )
            if not missing_user_inputs:
                missing_user_inputs = _build_missing_user_inputs(
                    job_snapshot=job_snapshot,
                    resume_snapshot=resume_snapshot,
                    missing_items=list(rule_result.evidence_map.get("missing_items", [])),
                )
            if not interview_focus_areas:
                interview_focus_areas = _build_interview_focus_areas(
                    gaps=gaps,
                    strengths=strengths,
                )
            evidence_map = _merge_evidence_map(
                base_map=rule_result.evidence_map,
                overlay_map=(
                    ai_payload.evidence_map_json.model_dump()
                    if ai_payload is not None
                    else {}
                ),
                resume_version=report.resume_version,
                job_version=report.job_version,
            )
            action_pack = (
                ai_payload.action_pack_json.model_dump()
                if ai_payload is not None
                else {
                    "resume_tailoring_tasks": [],
                    "interview_focus_areas": [],
                    "missing_user_inputs": [],
                }
            )
            if not action_pack["resume_tailoring_tasks"]:
                action_pack["resume_tailoring_tasks"] = resume_tailoring_tasks
            if not action_pack["interview_focus_areas"]:
                action_pack["interview_focus_areas"] = interview_focus_areas
            if not action_pack["missing_user_inputs"]:
                action_pack["missing_user_inputs"] = missing_user_inputs
            tailoring_plan = (
                ai_payload.tailoring_plan_json.model_dump()
                if ai_payload is not None
                else _build_tailoring_plan(
                    job_snapshot=job_snapshot,
                    tasks=resume_tailoring_tasks,
                    missing_items=list(evidence_map.get("missing_items", []) or []),
                    missing_user_inputs=missing_user_inputs,
                )
            )
            if not tailoring_plan["rewrite_tasks"]:
                tailoring_plan["rewrite_tasks"] = resume_tailoring_tasks
            tailoring_plan["must_add_evidence"] = _merge_unique_strings(
                list(tailoring_plan.get("must_add_evidence", []) or []),
                list(evidence_map.get("missing_items", []) or []),
            )[:8]
            if not tailoring_plan["missing_info_questions"]:
                tailoring_plan["missing_info_questions"] = missing_user_inputs
            if not tailoring_plan.get("target_summary"):
                tailoring_plan["target_summary"] = job_snapshot.raw_summary or job_snapshot.basic.title
            interview_blueprint = (
                ai_payload.interview_blueprint_json.model_dump()
                if ai_payload is not None
                else _build_interview_blueprint(
                    job_snapshot=job_snapshot,
                    fit_band=fit_band,
                    focus_areas=interview_focus_areas,
                )
            )
            if not interview_blueprint["focus_areas"]:
                interview_blueprint["focus_areas"] = interview_focus_areas
            if not interview_blueprint["question_pack"]:
                interview_blueprint = _build_interview_blueprint(
                    job_snapshot=job_snapshot,
                    fit_band=fit_band,
                    focus_areas=interview_focus_areas,
                )
            else:
                interview_blueprint["target_role"] = (
                    interview_blueprint.get("target_role")
                    or job_snapshot.basic.title
                )
                interview_blueprint["mode"] = "targeted_match_mvp"

            stale_status = (
                "stale"
                if resume.latest_version > report.resume_version
                or job.latest_version > report.job_version
                else "fresh"
            )
            scorecard = {
                "overall_score": round(overall_score, 2),
                "rule_score": round(rule_result.rule_score, 2),
                "semantic_score": semantic_score,
                "llm_judge_score": round(llm_judge_score, 2),
                "fit_band": fit_band,
                "llm_fit_band": ai_payload.fit_band if ai_payload is not None else None,
                "confidence": ai_payload.confidence if ai_payload is not None else None,
                "summary": (
                    ai_payload.summary
                    if ai_payload is not None
                    else "AI 校正暂不可用，当前报告基于规则匹配结果生成。"
                ),
                "reasoning": (
                    ai_payload.reasoning
                    if ai_payload is not None
                    else ai_reason
                ),
                "generation_mode": (
                    "hybrid_rule_semantic_llm"
                    if ai_payload is not None
                    else "rule_semantic_fallback"
                ),
                "dimension_scores": dimension_scores,
            }
            gap_taxonomy = {
                "must_fix": must_fix[:5],
                "should_fix": should_fix[:5],
                "watchlist": missing_user_inputs,
                "rule_gaps": rule_result.gaps[:5],
            }

            report.status = "success"
            report.fit_band = fit_band
            report.stale_status = stale_status
            report.overall_score = _to_decimal_score(overall_score)
            report.rule_score = _to_decimal_score(rule_result.rule_score)
            report.model_score = _to_decimal_score(llm_judge_score)
            report.dimension_scores_json = dimension_scores
            report.gap_json = {
                "strengths": strengths,
                "gaps": gaps,
                "actions": actions,
            }
            report.evidence_json = {
                **rule_result.evidence,
                "evidence_map": rule_result.evidence_map,
                "final_evidence_map": evidence_map,
                "scoring": {
                    "rule_score": round(rule_result.rule_score, 2),
                    "semantic_score": semantic_score,
                    "llm_judge_score": round(llm_judge_score, 2),
                    "overall_score": round(overall_score, 2),
                },
                "ai_generation": {
                    "provider": ai_provider_name,
                    "model": ai_model_name,
                    "status": ai_status,
                    "summary": (
                        ai_payload.summary
                        if ai_payload is not None
                        else "AI 校正未应用，已回退到规则匹配结果。"
                    ),
                    "reasoning": (
                        ai_payload.reasoning
                        if ai_payload is not None
                        else ai_reason
                    ),
                },
            }
            report.scorecard_json = scorecard
            report.evidence_map_json = evidence_map
            report.gap_taxonomy_json = gap_taxonomy
            report.action_pack_json = action_pack
            report.tailoring_plan_json = tailoring_plan
            report.interview_blueprint_json = interview_blueprint
            report.error_message = None

            previous_stage = job.status_stage
            job.latest_match_report_id = report.id
            job.recommended_resume_id = report.resume_id
            job.status_stage = _derive_job_status_stage(
                fit_band=fit_band,
                stale_status=stale_status,
                tailoring_task_count=len(resume_tailoring_tasks),
            )
            job.updated_by = job.user_id
            report.updated_by = report.user_id
            session.add(job)
            session.add(report)
            await _record_job_readiness_event(
                session,
                job=job,
                report=report,
                status_from=previous_stage,
                status_to=job.status_stage,
                reason="Match report generated successfully",
            )
            await session.commit()
        except Exception as exc:
            report.status = "failed"
            report.error_message = str(exc)
            session.add(report)
            await session.commit()


async def list_match_reports_by_job(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID,
) -> list[MatchReport]:
    await get_job_or_404(session, current_user=current_user, job_id=job_id)
    result = await session.execute(
        select(MatchReport)
        .where(
            MatchReport.user_id == current_user.id,
            MatchReport.jd_id == job_id,
        )
        .order_by(desc(MatchReport.created_at))
    )
    return list(result.scalars().all())


async def delete_match_report(
    session: AsyncSession,
    *,
    current_user: User,
    report_id: UUID,
) -> MatchReportDeleteResponse:
    report = await get_match_report_or_404(
        session, current_user=current_user, report_id=report_id
    )
    job = await session.get(JobDescription, report.jd_id)
    await session.delete(report)
    if job is not None and job.latest_match_report_id == report.id:
        next_report_result = await session.execute(
            select(MatchReport)
            .where(MatchReport.jd_id == job.id, MatchReport.id != report.id)
            .order_by(desc(MatchReport.created_at))
            .limit(1)
        )
        next_report = next_report_result.scalar_one_or_none()
        job.latest_match_report_id = next_report.id if next_report is not None else None
        session.add(job)
    await session.commit()
    return MatchReportDeleteResponse(message="Match report deleted successfully")
