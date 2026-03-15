from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException, ErrorCode
from app.models import MatchReport, User
from app.schemas.job import JobStructuredData
from app.schemas.match_report import (
    MatchReportCreateRequest,
    MatchReportDeleteResponse,
    MatchReportResponse,
)
from app.schemas.resume import ResumeStructuredData
from app.services.job import get_job_or_404, parse_job
from app.services.match_ai import (
    AIMatchCorrectionProvider,
    AIMatchCorrectionRequest,
    AIMatchCorrectionResult,
)
from app.services.match_engine import build_rule_match_result
from app.services.resume import get_resume_for_user


def serialize_match_report(report: MatchReport) -> MatchReportResponse:
    return MatchReportResponse(
        id=report.id,
        user_id=report.user_id,
        resume_id=report.resume_id,
        jd_id=report.jd_id,
        status=report.status,
        overall_score=report.overall_score,
        rule_score=report.rule_score,
        model_score=report.model_score,
        dimension_scores_json=report.dimension_scores_json or {},
        gap_json=report.gap_json or {},
        evidence_json=report.evidence_json or {},
        error_message=report.error_message,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _to_decimal_score(value: float) -> Decimal:
    return Decimal(str(round(value, 2))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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
    seen: set[tuple[str, str]] = set()

    for raw_item in items:
        title = str(raw_item.get("title", "")).strip()
        description = str(raw_item.get("description", "")).strip()
        if not title or not description:
            continue
        key = (title.lower(), description.lower())
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
            }
        )

    sanitized.sort(key=lambda item: (int(item["priority"]), str(item["title"]).lower()))
    for index, item in enumerate(sanitized, start=1):
        item["priority"] = index
    return sanitized[:5]


def _build_failed_ai_result(exc: Exception) -> AIMatchCorrectionResult:
    return AIMatchCorrectionResult(
        provider="unavailable",
        model=None,
        status="failed",
        delta=0.0,
        reasoning=str(exc).strip() or "AI correction failed",
    )


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
    ai_provider: AIMatchCorrectionProvider,
) -> MatchReport:
    if not payload.force_refresh:
        reused_report = await _get_latest_report_for_pair(
            session,
            current_user=current_user,
            job_id=job_id,
            resume_id=payload.resume_id,
        )
        if reused_report is not None:
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
        job = await parse_job(session, current_user=current_user, job_id=job_id)

    resume_snapshot = ResumeStructuredData.model_validate(resume.structured_json)
    job_snapshot = JobStructuredData.model_validate(job.structured_json)
    rule_result = build_rule_match_result(
        resume=resume_snapshot,
        resume_raw_text=resume.raw_text,
        job=job_snapshot,
    )

    try:
        ai_result = await ai_provider.correct(
            AIMatchCorrectionRequest(
                resume_snapshot=resume_snapshot.model_dump(),
                job_snapshot=job_snapshot.model_dump(),
                rule_score=rule_result.overall_score,
                dimension_scores=rule_result.dimension_scores,
                strengths=rule_result.strengths,
                gaps=rule_result.gaps,
                actions=rule_result.actions,
            )
        )
    except Exception as exc:
        ai_result = _build_failed_ai_result(exc)

    dimension_scores = {
        **rule_result.dimension_scores,
        "ai_correction_delta": round(float(ai_result.delta), 2),
    }
    strengths = _sanitize_insight_items([*rule_result.strengths, *ai_result.strengths])
    gaps = _sanitize_insight_items([*rule_result.gaps, *ai_result.gaps])
    actions = _sanitize_action_items([*rule_result.actions, *ai_result.actions])

    evidence = dict(rule_result.evidence)
    notes = list(evidence.get("notes", []))
    if ai_result.status == "applied":
        notes.append("AI 修正已在规则结果基础上做语义补偿。")
    elif ai_result.status == "skipped":
        notes.append("AI 修正未启用，当前结果完全由规则引擎生成。")
    elif ai_result.status == "failed":
        notes.append("AI 修正调用失败，当前结果已自动回退到规则引擎结果。")

    evidence["notes"] = notes
    evidence["ai_correction"] = ai_result.to_metadata()

    overall_score = max(0.0, min(100.0, rule_result.overall_score + float(ai_result.delta)))

    report = MatchReport(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        status="success",
        overall_score=_to_decimal_score(overall_score),
        rule_score=_to_decimal_score(rule_result.overall_score),
        model_score=_to_decimal_score(float(ai_result.delta)),
        dimension_scores_json=dimension_scores,
        gap_json={
            "strengths": strengths,
            "gaps": gaps,
            "actions": actions,
        },
        evidence_json=evidence,
        error_message=None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


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
    report = await get_match_report_or_404(session, current_user=current_user, report_id=report_id)
    await session.delete(report)
    await session.commit()
    return MatchReportDeleteResponse(message="Match report deleted successfully")
