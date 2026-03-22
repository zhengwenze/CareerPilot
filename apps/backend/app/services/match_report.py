from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ApiException, ErrorCode
from app.models import JobDescription, MatchReport, Resume, User
from app.schemas.match_report import MatchReportCreateRequest


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _tokenize(value: str) -> set[str]:
    return {token for token in _normalize_text(value).lower().replace("/", " ").split(" ") if token}


def _extract_resume_markdown(resume: Resume) -> str:
    artifacts = resume.parse_artifacts_json or {}
    return str(artifacts.get("canonical_resume_md") or resume.raw_text or "").strip()


def _build_report_payload(*, resume: Resume, job: JobDescription) -> dict[str, Any]:
    resume_text = _extract_resume_markdown(resume)
    job_text = job.jd_text.strip()
    resume_tokens = _tokenize(resume_text)
    job_tokens = _tokenize(job_text)
    matched = sorted(job_tokens & resume_tokens)
    missing = sorted(job_tokens - resume_tokens)
    score_ratio = len(matched) / max(len(job_tokens), 1)
    score = round(score_ratio * 100, 2)
    if score >= 75:
      fit_band = "excellent"
    elif score >= 55:
      fit_band = "strong"
    elif score >= 35:
      fit_band = "partial"
    else:
      fit_band = "weak"
    return {
        "fit_band": fit_band,
        "score": score,
        "matched": matched[:20],
        "missing": missing[:20],
    }


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
    result = await session.execute(
        select(MatchReport)
        .where(
            MatchReport.user_id == current_user.id,
            MatchReport.jd_id == job_id,
            MatchReport.resume_id == payload.resume_id,
            MatchReport.stale_status == "fresh",
            MatchReport.status == "success",
        )
        .order_by(desc(MatchReport.created_at))
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing is not None and not payload.force_refresh:
        return existing

    resume = await session.get(Resume, payload.resume_id)
    job = await session.get(JobDescription, job_id)
    if resume is None or job is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Resume or job not found for match report generation",
        )

    report = MatchReport(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        resume_version=resume.latest_version,
        job_version=job.latest_version,
        status="pending",
        stale_status="fresh",
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def process_match_report(
    *,
    report_id: UUID,
    session_factory: async_sessionmaker[AsyncSession],
    settings,
) -> None:
    del settings
    async with session_factory() as session:
        report = await session.get(MatchReport, report_id)
        if report is None:
            return
        resume = await session.get(Resume, report.resume_id)
        job = await session.get(JobDescription, report.jd_id)
        if resume is None or job is None:
            report.status = "failed"
            report.error_message = "Resume or job not found"
            session.add(report)
            await session.commit()
            return

        payload = _build_report_payload(resume=resume, job=job)
        report.status = "success"
        report.fit_band = payload["fit_band"]
        report.overall_score = Decimal(str(payload["score"]))
        report.rule_score = Decimal(str(payload["score"]))
        report.model_score = Decimal(str(payload["score"]))
        report.dimension_scores_json = {"relevance": payload["score"]}
        report.gap_json = {
            "strengths": payload["matched"][:8],
            "gaps": payload["missing"][:8],
            "actions": [],
        }
        report.evidence_json = {
            "matched_resume_fields": {},
            "matched_jd_fields": {"keywords": payload["matched"][:12]},
            "missing_items": payload["missing"][:12],
            "notes": [],
        }
        report.scorecard_json = {
            "overall_score": payload["score"],
            "fit_band": payload["fit_band"],
        }
        report.evidence_map_json = {
            "matched_jd_fields": {"keywords": payload["matched"][:12]},
            "missing_items": payload["missing"][:12],
        }
        report.gap_taxonomy_json = {}
        report.action_pack_json = {}
        report.tailoring_plan_json = {
            "target_summary": job.title,
            "must_add_evidence": payload["missing"][:8],
        }
        report.interview_blueprint_json = {}
        report.error_message = None
        session.add(report)
        await session.commit()
