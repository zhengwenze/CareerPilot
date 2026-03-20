from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import (
    JobReadinessEvent,
    MatchReport,
    Resume,
    ResumeOptimizationSession,
    User,
)
from app.schemas.job import JobCreateRequest
from app.schemas.match_report import MatchReportCreateRequest
from app.schemas.resume import ResumeStructuredData
from app.schemas.resume_optimization import ResumeOptimizationSessionCreateRequest
from app.services.job import create_job, process_job_parse_job
from app.services.match_report import create_match_report, process_match_report
from app.services.mock_interview import _compact_optimization_snapshot
from app.services.resume_optimizer import (
    apply_resume_optimization_session,
    create_resume_optimization_session,
    generate_resume_optimization_suggestions,
    get_resume_optimization_markdown_download,
    get_resume_optimization_session,
)


def _mock_match_ai_payload() -> dict[str, object]:
    return {
        "overall_score": 80,
        "fit_band": "strong",
        "summary": "简历与岗位方向整体匹配，但仍需补强结果量化与协作细节。",
        "reasoning": "技能方向和岗位职责基本一致，但部分高价值证据表达还不够充分。",
        "confidence": 0.84,
        "strengths": [
            {
                "label": "增长分析",
                "reason": "简历中已有直接项目和实习经历支撑。",
                "severity": "high",
            }
        ],
        "must_fix": [
            {
                "label": "量化结果",
                "reason": "需要补充指标变化和业务影响。",
                "severity": "high",
            }
        ],
        "should_fix": [
            {
                "label": "协作场景",
                "reason": "可再补充跨团队推进细节。",
                "severity": "medium",
            }
        ],
        "evidence_map_json": {
            "matched_resume_fields": {
                "skills": ["Python", "SQL", "Tableau"],
            },
            "matched_jd_fields": {
                "required_skills": ["Python", "SQL", "Tableau"],
                "responsibilities": ["增长分析", "实验分析", "指标体系建设"],
            },
            "missing_items": ["量化结果"],
            "notes": ["AI 已根据岗位目标生成最终报告。"],
            "candidate_profile": {"skills": ["Python", "SQL", "Tableau"]},
        },
        "action_pack_json": {
            "resume_tailoring_tasks": [
                {
                    "priority": 1,
                    "title": "补充量化结果",
                    "instruction": "在工作经历中补充指标变化和业务影响。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "interview_focus_areas": [
                {
                    "topic": "量化结果表达",
                    "reason": "面试中需要清楚说明业务结果。",
                    "priority": "high",
                }
            ],
            "missing_user_inputs": [
                {
                    "field": "metrics",
                    "question": "是否有增长分析相关的结果指标可补充？",
                }
            ],
        },
        "tailoring_plan_json": {
            "target_summary": "增长数据分析师",
            "rewrite_tasks": [
                {
                    "priority": 1,
                    "title": "补充量化结果",
                    "instruction": "在工作经历中补充指标变化和业务影响。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "must_add_evidence": ["量化结果"],
            "missing_info_questions": [
                {
                    "field": "metrics",
                    "question": "是否有增长分析相关的结果指标可补充？",
                }
            ],
        },
        "interview_blueprint_json": {
            "target_role": "增长数据分析师",
            "focus_areas": [
                {
                    "topic": "量化结果表达",
                    "reason": "岗位需要结果导向表达。",
                    "priority": "high",
                }
            ],
            "question_pack": [
                {
                    "topic": "量化结果表达",
                    "question": "请描述一次你推动增长分析结果落地的经历。",
                    "intent": "验证结果表达和业务影响意识。",
                }
            ],
            "follow_up_rules": ["若未提及指标，则追问具体结果。"],
            "rubric": [
                {
                    "dimension": "量化结果表达",
                    "weight": 30,
                    "criteria": "是否说清背景、动作、指标和影响。",
                }
            ],
        },
    }


def _mock_optimizer_ai_payload(
    *,
    summary: str,
    work_bullet: str,
    project_bullet: str,
) -> dict[str, object]:
    return {
        "summary": summary,
        "work_experience_items": [
            {
                "id": "work_1",
                "bullets": [
                    {
                        "id": "work_1_b1",
                        "text": work_bullet,
                        "kind": "achievement",
                        "metrics": [],
                        "skills_used": ["Python", "SQL"],
                        "source_refs": ["work_1"],
                    }
                ],
            }
        ],
        "project_items": [
            {
                "id": "proj_1",
                "bullets": [
                    {
                        "id": "proj_1_b1",
                        "text": project_bullet,
                        "kind": "achievement",
                        "metrics": [],
                        "skills_used": ["Python", "SQL", "Tableau"],
                        "source_refs": ["proj_1"],
                    }
                ],
            }
        ],
        "unresolved_items": [
            {
                "task_key": "task-1",
                "reason": "量化结果仍缺少明确数字，因此保持为事实约束式表述。",
            }
        ],
        "editor_notes": ["仅基于原始结构化简历与 match_report 证据进行改写。"],
    }


def _optimizer_settings() -> Settings:
    return Settings(
        resume_ai_api_key="test-key",
        resume_ai_model="MiniMax-M2.5",
        resume_ai_base_url="https://api.minimaxi.com/anthropic",
    )


def _resume_structured_data() -> ResumeStructuredData:
    return ResumeStructuredData(
        basic_info={
            "name": "郑文泽",
            "email": "zheng@example.com",
            "phone": "13800138000",
            "location": "上海",
            "summary": "负责数据分析与实验复盘。",
        },
        education=["新疆大学 软件工程 本科 2023.09-2027.06"],
        work_experience=["CareerPilot 数据分析实习生 推进指标体系与增长分析"],
        projects=["业务增长分析平台 从0到1搭建实验看板"],
        skills={
            "technical": ["Python", "SQL"],
            "tools": ["Tableau"],
            "languages": ["English"],
        },
        certifications=["百度之星金奖"],
    )


async def _create_parsed_resume(session: AsyncSession, *, user: User) -> Resume:
    resume = Resume(
        id=uuid4(),
        user_id=user.id,
        file_name="resume.pdf",
        file_url="minio://career-pilot/resume.pdf",
        storage_bucket="career-pilot",
        storage_object_key=f"resumes/{user.id}/resume.pdf",
        content_type="application/pdf",
        file_size=1024,
        parse_status="success",
        parse_error=None,
        raw_text=(
            "郑文泽 上海 数据分析 SQL Python 指标体系 实验分析 "
            "增长分析 CareerPilot 数据分析实习生"
        ),
        structured_json=_resume_structured_data().model_dump(),
        latest_version=1,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def _create_ready_match_report(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[UUID, UUID, UUID]:
    async def fake_request_json_completion(**_: object) -> dict[str, object]:
        return _mock_match_ai_payload()

    monkeypatch.setattr(
        "app.services.match_ai.request_json_completion",
        fake_request_json_completion,
    )

    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=user)
        job, parse_job = await create_job(
            session,
            current_user=user,
            payload=JobCreateRequest(
                title="增长数据分析师",
                company="CareerPilot",
                job_city="上海",
                employment_type="全职",
                source_name="Boss直聘",
                source_url="https://example.com/jobs/optimizer",
                priority=2,
                jd_text=(
                    "岗位职责\n"
                    "- 负责增长分析、实验分析与指标体系建设\n"
                    "- 联动业务团队推进优化策略落地\n"
                    "任职要求\n"
                    "- 本科及以上，2年以上经验\n"
                    "- 熟练使用 Python、SQL、Tableau"
                ),
            ),
        )
        resume_id = resume.id
        job_id = job.id
        parse_job_id = parse_job.id

    await process_job_parse_job(
        job_id=job_id,
        parse_job_id=parse_job_id,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        report = await create_match_report(
            session,
            current_user=user,
            job_id=job_id,
            payload=MatchReportCreateRequest(
                resume_id=resume_id,
                force_refresh=True,
            ),
        )
        report_id = report.id

    await process_match_report(
        report_id=report_id,
        session_factory=session_factory,
        settings=Settings(
            match_ai_provider="minimax",
            match_ai_base_url="https://api.minimaxi.com/anthropic",
            match_ai_api_key="test-key",
            match_ai_model="MiniMax-M2.5",
        ),
    )
    return resume_id, job_id, report_id


async def _override_optimizer_inputs(
    session: AsyncSession,
    *,
    report_id: UUID,
    rewrite_tasks: list[dict[str, object]],
    must_add_evidence: list[str],
    matched_jd_fields: dict[str, list[str]],
    gap_labels: list[str],
) -> None:
    report = await session.get(MatchReport, report_id)
    assert report is not None

    report.tailoring_plan_json = {
        **(report.tailoring_plan_json or {}),
        "target_summary": "增长数据分析师",
        "rewrite_tasks": rewrite_tasks,
        "must_add_evidence": must_add_evidence,
        "missing_info_questions": [
            {
                "field": "missing_evidence",
                "question": "请补充与目标岗位直接相关的事实证据。",
            }
        ],
    }
    report.evidence_map_json = {
        **(report.evidence_map_json or {}),
        "matched_jd_fields": matched_jd_fields,
    }
    report.gap_json = {
        **(report.gap_json or {}),
        "gaps": [
            {
                "label": label,
                "reason": f"需要补充 {label} 相关证据。",
                "severity": "high",
            }
            for label in gap_labels
        ],
    }
    session.add(report)
    await session.commit()


@pytest.mark.asyncio
async def test_resume_optimizer_flow_generates_structured_outputs_applies_and_downloads(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async def fake_optimizer_completion(**_: object) -> dict[str, object]:
        return _mock_optimizer_ai_payload(
            summary="负责数据分析与实验复盘，目标岗位聚焦增长数据分析师。",
            work_bullet="推进指标体系与增长分析，并沉淀实验分析复盘流程。",
            project_bullet="从0到1搭建实验看板，支撑业务增长分析平台的持续复盘。",
        )

    monkeypatch.setattr(
        "app.services.resume_optimizer_ai.request_json_completion",
        fake_optimizer_completion,
    )

    async with session_factory() as session:
        session_record, _resume, _job, _report = await create_resume_optimization_session(
            session,
            current_user=test_user,
            payload=ResumeOptimizationSessionCreateRequest(match_report_id=report_id),
        )
        session_id = session_record.id
        assert session_record.status == "draft"
        assert session_record.applied_resume_version is None

        generated = await generate_resume_optimization_suggestions(
            session,
            current_user=test_user,
            session_id=session_id,
            settings=_optimizer_settings(),
        )
        assert generated.status == "ready"
        assert generated.optimized_resume_json is not None
        assert generated.optimized_resume_json.basic_info.summary == (
            "负责数据分析与实验复盘，目标岗位聚焦增长数据分析师。"
        )
        assert generated.rewrite_tasks[0].target_requirement != ""
        assert generated.rewrite_tasks[0].available_evidence
        assert generated.fact_check_report_json["summary"]["high_risk_count"] == 0
        assert generated.optimized_resume_md.startswith("# 郑文泽")
        assert "## Work Experience" in generated.optimized_resume_md
        assert generated.downstream_contract.prohibited_source == (
            "resume_optimization_session.optimized_resume_md"
        )

        markdown_content, file_name = await get_resume_optimization_markdown_download(
            session,
            current_user=test_user,
            session_id=session_id,
        )
        assert file_name.endswith(".md")
        assert "## Projects" in markdown_content

        apply_result = await apply_resume_optimization_session(
            session,
            current_user=test_user,
            session_id=session_id,
        )
        assert apply_result.resume_id == resume_id
        assert apply_result.applied_resume_version == 2
        assert apply_result.downstream_fact_source == "resume.structured_json"

        refreshed = await get_resume_optimization_session(
            session,
            current_user=test_user,
            session_id=session_id,
        )
        assert refreshed.status == "applied"
        assert refreshed.applied_resume_version == 2
        assert refreshed.is_stale is True

    async with session_factory() as session:
        persisted_resume = await session.get(Resume, resume_id)
        persisted_report = await session.get(MatchReport, report_id)
        persisted_session = await session.get(ResumeOptimizationSession, session_id)
        readiness_events = await session.scalars(
            select(JobReadinessEvent).where(
                JobReadinessEvent.match_report_id == report_id,
                JobReadinessEvent.status_to == "tailoring_applied",
            )
        )

        assert persisted_resume is not None
        assert persisted_report is not None
        assert persisted_session is not None
        assert persisted_resume.latest_version == 2
        assert persisted_report.stale_status == "stale"
        assert persisted_session.status == "applied"
        assert persisted_session.applied_resume_version == 2
        structured_resume = ResumeStructuredData.model_validate(persisted_resume.structured_json)
        assert structured_resume.basic_info.summary == "负责数据分析与实验复盘，目标岗位聚焦增长数据分析师。"
        assert (
            structured_resume.work_experience_items[0].bullets[0].text
            == "推进指标体系与增长分析，并沉淀实验分析复盘流程。"
        )
        assert len(list(readiness_events)) >= 1


@pytest.mark.asyncio
async def test_resume_optimizer_routes_cross_section_task_to_projects(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async def fake_optimizer_completion(**_: object) -> dict[str, object]:
        return _mock_optimizer_ai_payload(
            summary="负责数据分析与实验复盘，聚焦实验分析场景。",
            work_bullet="推进指标体系与增长分析。",
            project_bullet="从0到1搭建实验看板，围绕实验分析与业务复盘沉淀项目表达。",
        )

    monkeypatch.setattr(
        "app.services.resume_optimizer_ai.request_json_completion",
        fake_optimizer_completion,
    )

    async with session_factory() as session:
        await _override_optimizer_inputs(
            session,
            report_id=report_id,
            rewrite_tasks=[
                {
                    "priority": 1,
                    "title": "实验看板搭建",
                    "instruction": "在项目经历中突出实验看板与业务分析场景。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            must_add_evidence=["实验分析结果"],
            matched_jd_fields={"responsibilities": ["实验看板", "业务分析"]},
            gap_labels=["实验分析结果"],
        )

        session_record, _resume, _job, _report = await create_resume_optimization_session(
            session,
            current_user=test_user,
            payload=ResumeOptimizationSessionCreateRequest(match_report_id=report_id),
        )
        generated = await generate_resume_optimization_suggestions(
            session,
            current_user=test_user,
            session_id=session_record.id,
            settings=_optimizer_settings(),
        )

        assert generated.rewrite_tasks[0].target_section == "projects"
        assert generated.optimized_resume_json is not None
        assert (
            generated.optimized_resume_json.project_items[0].bullets[0].text
            == "从0到1搭建实验看板，围绕实验分析与业务复盘沉淀项目表达。"
        )
        assert generated.fact_check_report_json["summary"]["high_risk_count"] == 0


@pytest.mark.asyncio
async def test_resume_optimizer_reports_missing_evidence_without_inventing_facts_when_ai_skipped(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async with session_factory() as session:
        await _override_optimizer_inputs(
            session,
            report_id=report_id,
            rewrite_tasks=[
                {
                    "priority": 1,
                    "title": "生命周期运营",
                    "instruction": "突出留存策略制定与用户分层运营经验。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            must_add_evidence=["留存结果"],
            matched_jd_fields={"responsibilities": ["生命周期运营", "留存策略"]},
            gap_labels=["留存策略"],
        )

        session_record, _resume, _job, _report = await create_resume_optimization_session(
            session,
            current_user=test_user,
            payload=ResumeOptimizationSessionCreateRequest(match_report_id=report_id),
        )
        generated = await generate_resume_optimization_suggestions(
            session,
            current_user=test_user,
            session_id=session_record.id,
            settings=None,
        )

        assert generated.status == "ready"
        assert generated.diagnosis_json["ai_status"]["status"] == "skipped"
        assert "禁止新增经历、技能、数字或时间" in generated.rewrite_tasks[0].risk_note
        assert generated.fact_check_report_json["summary"]["passed"] is True
        assert generated.optimized_resume_json is not None
        assert generated.optimized_resume_json.work_experience_items[0].company.startswith("CareerPilot")
        assert generated.optimized_resume_json.project_items[0].name.startswith("业务增长分析平台")


@pytest.mark.asyncio
async def test_resume_optimizer_snapshot_boundary_exposes_structured_object_not_markdown(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async def fake_optimizer_completion(**_: object) -> dict[str, object]:
        return _mock_optimizer_ai_payload(
            summary="负责数据分析与实验复盘，目标岗位聚焦增长数据分析师。",
            work_bullet="推进指标体系与增长分析，并沉淀实验分析复盘流程。",
            project_bullet="从0到1搭建实验看板，支撑业务增长分析平台的持续复盘。",
        )

    monkeypatch.setattr(
        "app.services.resume_optimizer_ai.request_json_completion",
        fake_optimizer_completion,
    )

    async with session_factory() as session:
        session_record, _resume, _job, _report = await create_resume_optimization_session(
            session,
            current_user=test_user,
            payload=ResumeOptimizationSessionCreateRequest(match_report_id=report_id),
        )
        await generate_resume_optimization_suggestions(
            session,
            current_user=test_user,
            session_id=session_record.id,
            settings=_optimizer_settings(),
        )

        refreshed_session = await session.get(ResumeOptimizationSession, session_record.id)
        assert refreshed_session is not None
        snapshot = _compact_optimization_snapshot(refreshed_session)

        assert snapshot["structured_fact_source"] == (
            "resume_optimization_session.optimized_resume_json"
        )
        assert snapshot["markdown_is_fact_source"] is False
        assert "optimized_resume_json" in snapshot
        assert "draft_sections_json" not in snapshot
        assert "selected_tasks_json" not in snapshot
