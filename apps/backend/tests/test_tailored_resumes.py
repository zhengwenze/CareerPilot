from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.models import JobDescription, MatchReport, Resume, ResumeOptimizationSession
from app.schemas.ai_runtime import ContentSegment, SegmentExplanation, TaskState
from app.schemas.resume import (
    ResumeBasicInfo,
    ResumeExperienceBullet,
    ResumeProjectItem,
    ResumeStructuredData,
    ResumeWorkExperienceItem,
)
from app.schemas.tailored_resume import TailoredResumeDocument
from app.services import tailored_resume as tailored_resume_service
from app.services.job import process_job_parse_job
from app.services.tailored_resume_autostart import (
    maybe_autostart_tailored_resume,
    maybe_autostart_tailored_resume_for_job,
)

from conftest import create_test_user


async def _seed_tailored_resume_dependencies(db_session, *, user, suffix: str) -> tuple[Resume, JobDescription]:
    structured_resume = ResumeStructuredData(
        basic_info=ResumeBasicInfo(
            name="测试候选人",
            title="前端工程师",
            email="candidate@example.com",
            summary="负责复杂前端项目交付与组件体系建设。",
        ),
        work_experience_items=[
            ResumeWorkExperienceItem(
                id="work_1",
                company="CareerPilot",
                title="前端工程师",
                start_date="2023-01",
                end_date="至今",
                bullets=[
                    ResumeExperienceBullet(
                        id="work_1_b1",
                        text="负责后台管理系统重构和组件复用。",
                    )
                ],
            )
        ],
        project_items=[
            ResumeProjectItem(
                id="proj_1",
                name="增长平台",
                role="前端负责人",
                start_date="2023-06",
                end_date="2024-02",
                summary="负责增长实验平台搭建。",
                bullets=[
                    ResumeExperienceBullet(
                        id="proj_1_b1",
                        text="建设实验配置与发布流程。",
                    )
                ],
            )
        ],
    )
    resume = Resume(
        user_id=user.id,
        file_name=f"resume-{suffix}.pdf",
        file_url=f"https://example.test/resume-{suffix}.pdf",
        storage_bucket="test",
        storage_object_key=f"resume-{suffix}.pdf",
        content_type="application/pdf",
        file_size=123,
        parse_status="success",
        raw_text="# Resume",
        structured_json=structured_resume.model_dump(mode="json"),
        parse_artifacts_json={"canonical_resume_md": "# Resume"},
        created_by=user.id,
        updated_by=user.id,
    )
    job = JobDescription(
        user_id=user.id,
        title=f"Senior Frontend Engineer {suffix}",
        jd_text=f"Need React leadership, experiment platform and performance optimisation for {suffix}",
        latest_version=1,
        priority=3,
        status_stage="interview_ready",
        parse_status="success",
        structured_json={"title": f"Senior Frontend Engineer {suffix}"},
        competency_graph_json={},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add_all([resume, job])
    await db_session.commit()
    return resume, job


async def _seed_ready_job(
    db_session,
    *,
    user,
    suffix: str,
) -> JobDescription:
    job = JobDescription(
        user_id=user.id,
        title=f"Backend Engineer {suffix}",
        jd_text=f"Need APIs, SQLAlchemy and delivery ownership for {suffix}",
        latest_version=1,
        priority=3,
        status_stage="interview_ready",
        parse_status="success",
        structured_json={"title": f"Backend Engineer {suffix}"},
        competency_graph_json={},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(job)
    await db_session.commit()
    return job


def _fake_rewrite_response() -> dict[str, object]:
    return {
        "summary": "主导复杂前端项目与组件体系建设，能够支撑岗位对 React 与协作能力的要求。",
        "work_experience_items": [
            {
                "id": "work_1",
                "bullets": [
                    {
                        "id": "work_1_b1",
                        "text": "主导后台管理系统重构，推动组件复用与交付效率提升。",
                        "kind": "responsibility",
                        "metrics": [],
                        "skills_used": ["React"],
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
                        "text": "建设实验配置与发布流程，支撑增长实验平台稳定迭代。",
                        "kind": "responsibility",
                        "metrics": [],
                        "skills_used": ["React"],
                        "source_refs": ["proj_1"],
                    }
                ],
            }
        ],
        "unresolved_items": [],
        "editor_notes": ["已优先强化岗位相关的 React 与增长平台经历。"],
    }


def _pdf_style_resume_markdown() -> str:
    return "\n".join(
        [
            "**郑文泽** 手机：17590522997 | 邮箱：2017160177@qq.com | 北京",
            "",
            "## **教育背景**",
            "",
            "## **新疆大学（211 / 双一流）**",
            "",
            "本科 / 软件工程",
            "2023.09 – 2027.06 GPA 3.73，专业排名 50/800",
            "",
            "- **竞赛获奖：** 百度之星省赛金奖；RoboCup 新疆一等奖",
            "",
            "## **项目经历**",
            "",
            "## **职点迷津**",
            "",
            "https://gitee.com/zwz050418/career-pilot.git",
            "智能求职工作台；React + Next.js + FastAPI",
            "- 负责简历解析、岗位匹配、优化建议生成等核心链路开发。",
            "",
            "## **专业技能**",
            "",
            "- React",
            "- FastAPI",
            "- PostgreSQL",
        ]
    )


def _build_match_report(*, user_id, resume: Resume, job: JobDescription) -> MatchReport:
    return MatchReport(
        user_id=user_id,
        resume_id=resume.id,
        jd_id=job.id,
        resume_version=resume.latest_version,
        job_version=job.latest_version,
        status="success",
        stale_status="fresh",
        fit_band="strong",
        overall_score=Decimal("88.00"),
        rule_score=Decimal("88.00"),
        model_score=Decimal("88.00"),
        dimension_scores_json={"relevance": 88},
        gap_json={"strengths": ["React"], "gaps": [], "actions": []},
        evidence_json={},
        scorecard_json={"overall_score": 88, "fit_band": "strong"},
        evidence_map_json={"matched_jd_fields": {"keywords": ["React"]}},
        gap_taxonomy_json={},
        action_pack_json={},
        tailoring_plan_json={},
        interview_blueprint_json={},
        created_by=user_id,
        updated_by=user_id,
    )


async def test_tailored_resume_optimize_returns_processing_then_persists_segments(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="demo")

    async def fake_request_json_completion(*, config, instructions, payload, max_tokens=4000):
        del config, instructions, payload, max_tokens
        return _fake_rewrite_response()

    monkeypatch.setattr(tailored_resume_service, "request_json_completion", fake_request_json_completion)

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 200
    workflow = response.json()["data"]
    assert workflow["tailored_resume"]["task_state"]["status"] == "processing"
    assert workflow["tailored_resume"]["display_status"] == "processing"
    assert len(workflow["tailored_resume"]["segments"]) == 6
    assert workflow["tailored_resume"]["downloadable"] is False

    await tailored_resume_service.process_tailored_resume_workflow(
        session_id=UUID(workflow["tailored_resume"]["session_id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/tailored-resumes/workflows/{workflow['tailored_resume']['session_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    completed = response.json()["data"]
    assert completed["tailored_resume"]["task_state"]["status"] == "success"
    assert completed["tailored_resume"]["display_status"] == "success"
    assert completed["tailored_resume"]["document"]["markdown"]
    assert len(completed["tailored_resume"]["segments"]) == 6
    assert completed["tailored_resume"]["downloadable"] is True
    assert completed["tailored_resume"]["retryable"] is False
    segments_by_key = {
        segment["key"]: segment for segment in completed["tailored_resume"]["segments"]
    }
    assert segments_by_key["summary"]["status"] == "success"
    assert segments_by_key["summary"]["suggested_text"] == _fake_rewrite_response()["summary"]
    assert segments_by_key["summary"]["explanation"]["what"] == "已对摘要做改写。"
    assert "工作经历" in segments_by_key["experience"]["explanation"]["value"]
    assert segments_by_key["projects"]["suggested_text"] != segments_by_key["projects"]["original_text"]
    assert segments_by_key["education"]["original_text"] == ""
    assert segments_by_key["education"]["suggested_text"] == ""
    assert segments_by_key["education"]["explanation"]["what"] == "该模块无原始内容。"
    assert segments_by_key["skills"]["explanation"]["what"] == "该模块无原始内容。"
    assert segments_by_key["summary"]["explanation"]["what"] != segments_by_key["projects"]["explanation"]["what"]


async def test_tailored_resume_optimize_requires_structured_resume_ready(
    app, client, db_session
):
    user, token = await create_test_user(db_session, email="tailored-structured-required@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="no-structured")
    resume.structured_json = None
    db_session.add(resume)
    await db_session.commit()

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 409
    assert (
        response.json()["error"]["message"]
        == "主简历已完成 Markdown 解析，但尚未完成结构化。请先保存主简历，生成结构化内容后再生成定制简历。"
    )


async def test_tailored_resume_optimize_accepts_resume_after_pdf_style_structured_save(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored-pdf-style-structured@example.com")
    markdown = _pdf_style_resume_markdown()
    resume = Resume(
        user_id=user.id,
        file_name="resume-pdf-style.pdf",
        file_url="https://example.test/resume-pdf-style.pdf",
        storage_bucket="test",
        storage_object_key="resume-pdf-style.pdf",
        content_type="application/pdf",
        file_size=123,
        parse_status="success",
        raw_text=markdown,
        structured_json=None,
        parse_artifacts_json={"canonical_resume_md": markdown},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(resume)
    await db_session.commit()

    job = await _seed_ready_job(db_session, user=user, suffix="pdf-style")

    save_response = await client.put(
        f"/resumes/{resume.id}/structured",
        headers={"Authorization": f"Bearer {token}"},
        json={"markdown": markdown},
    )
    assert save_response.status_code == 200
    assert save_response.json()["data"]["structured_json"]["basic_info"]["name"] == "郑文泽"

    optimize_response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert optimize_response.status_code == 200
    workflow = optimize_response.json()["data"]
    assert workflow["tailored_resume"]["task_state"]["status"] == "processing"
    assert workflow["tailored_resume"]["display_status"] == "processing"


async def test_tailored_resume_rewrite_payload_includes_original_resume_markdown(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored-markdown-payload@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="payload")
    captured_payload: dict[str, object] = {}

    async def fake_request_json_completion(*, config, instructions, payload, max_tokens=4000):
        del config, instructions, max_tokens
        captured_payload.update(payload)
        return _fake_rewrite_response()

    monkeypatch.setattr(tailored_resume_service, "request_json_completion", fake_request_json_completion)

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 200
    workflow = response.json()["data"]

    await tailored_resume_service.process_tailored_resume_workflow(
        session_id=UUID(workflow["tailored_resume"]["session_id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    assert captured_payload["original_resume_markdown"] == "# Resume"


async def test_tailored_resume_workflow_list_returns_processing_items(app, client, db_session, monkeypatch):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored-list@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="list")

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 200
    created = response.json()["data"]

    response = await client.get(
        "/tailored-resumes/workflows",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    workflows = response.json()["data"]
    listed = next(
        workflow
        for workflow in workflows
        if workflow["tailored_resume"]["session_id"] == created["tailored_resume"]["session_id"]
    )
    assert listed["tailored_resume"]["task_state"]["status"] == "processing"
    assert listed["tailored_resume"]["display_status"] == "processing"
    assert len(listed["tailored_resume"]["segments"]) == 6


async def test_tailored_resume_scheduler_updates_workflow_progress_and_completes(
    app, client, db_session, monkeypatch
):
    user, token = await create_test_user(db_session, email="tailored-scheduler@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="scheduler")

    async def fake_generate_rewrite_projection(*, source_resume, original_resume_markdown, job, report, settings):
        del original_resume_markdown, job, report, settings
        await asyncio.sleep(0.15)
        return source_resume.model_copy(deep=True), ["scheduler test"]

    monkeypatch.setattr(
        tailored_resume_service,
        "_generate_rewrite_projection",
        fake_generate_rewrite_projection,
    )

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 200
    workflow = response.json()["data"]
    session_id = workflow["tailored_resume"]["session_id"]
    assert workflow["tailored_resume"]["display_status"] == "processing"

    seen_statuses: set[str] = set()
    latest_payload = workflow
    for _ in range(20):
        await asyncio.sleep(0.05)
        response = await client.get(
            f"/tailored-resumes/workflows/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        latest_payload = response.json()["data"]
        seen_statuses.add(latest_payload["tailored_resume"]["display_status"])
        if latest_payload["tailored_resume"]["display_status"] == "success":
            break

    assert "segment_progress" in seen_statuses
    assert latest_payload["tailored_resume"]["display_status"] == "success"
    assert latest_payload["tailored_resume"]["downloadable"] is True
    assert latest_payload["tailored_resume"]["document"]["markdown"].strip()


async def test_tailored_resume_failure_returns_error_message_and_retryable(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored-failure@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="failure")

    def fake_finalize_document(*, document, source_resume, original_markdown, job, job_keywords):
        del document, source_resume, original_markdown, job, job_keywords
        raise RuntimeError("builder exploded")

    monkeypatch.setattr(tailored_resume_service, "_finalize_document", fake_finalize_document)

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 200
    workflow = response.json()["data"]

    await tailored_resume_service.process_tailored_resume_workflow(
        session_id=UUID(workflow["tailored_resume"]["session_id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/tailored-resumes/workflows/{workflow['tailored_resume']['session_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    failed = response.json()["data"]
    assert failed["tailored_resume"]["display_status"] == "failed"
    assert failed["tailored_resume"]["retryable"] is True
    assert failed["tailored_resume"]["downloadable"] is False
    assert failed["tailored_resume"]["error_message"] == "builder exploded"

    response = await client.get(
        f"/tailored-resumes/workflows/{workflow['tailored_resume']['session_id']}/download-markdown",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


async def test_tailored_resume_empty_result_is_not_reported_as_success(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored-empty@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="empty")

    original_finalize = tailored_resume_service._finalize_document

    def fake_finalize_document(*, document, source_resume, original_markdown, job, job_keywords):
        finalized_document, projected_resume, fact_check_report = original_finalize(
            document=document,
            source_resume=source_resume,
            original_markdown=original_markdown,
            job=job,
            job_keywords=job_keywords,
        )
        finalized_document.markdown = "   "
        return finalized_document, projected_resume, fact_check_report

    monkeypatch.setattr(tailored_resume_service, "_finalize_document", fake_finalize_document)

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 200
    workflow = response.json()["data"]

    await tailored_resume_service.process_tailored_resume_workflow(
        session_id=UUID(workflow["tailored_resume"]["session_id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/tailored-resumes/workflows/{workflow['tailored_resume']['session_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    empty_result = response.json()["data"]
    assert empty_result["tailored_resume"]["display_status"] == "empty_result"
    assert empty_result["tailored_resume"]["result_is_empty"] is True
    assert empty_result["tailored_resume"]["downloadable"] is False
    assert empty_result["tailored_resume"]["retryable"] is True
    assert empty_result["tailored_resume"]["error_message"] == "生成流程已结束，但未产出可下载的优化简历内容。"


async def test_tailored_resume_legacy_ready_status_maps_to_success_and_downloads(
    app, client, db_session
):
    user, token = await create_test_user(db_session, email="tailored-ready@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="ready")

    report = _build_match_report(user_id=user.id, resume=resume, job=job)
    db_session.add(report)
    await db_session.flush()

    session_record = ResumeOptimizationSession(
        user_id=user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        source_resume_version=resume.latest_version,
        source_job_version=job.latest_version,
        status="ready",
        tailored_resume_json=TailoredResumeDocument().model_dump(mode="json"),
        tailored_resume_md="# Tailored Resume\n\n## Summary\n- ready state markdown",
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(session_record)
    await db_session.commit()

    response = await client.get(
        f"/tailored-resumes/workflows/{session_record.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    workflow = response.json()["data"]
    assert workflow["tailored_resume"]["display_status"] == "success"
    assert workflow["tailored_resume"]["downloadable"] is True
    assert workflow["tailored_resume"]["retryable"] is False

    response = await client.get(
        f"/tailored-resumes/workflows/{session_record.id}/download-markdown",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "# Tailored Resume" in response.text


async def test_tailored_resume_retry_and_event_recording_preserve_completed_segments(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored-retry@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="retry")

    response = await client.post(
        "/tailored-resumes/optimize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "resume_id": str(resume.id),
            "job_id": str(job.id),
            "force_refresh": True,
        },
    )
    assert response.status_code == 200
    workflow = response.json()["data"]
    session_id = UUID(workflow["tailored_resume"]["session_id"])

    session_query = await db_session.execute(
        select(ResumeOptimizationSession).where(ResumeOptimizationSession.id == session_id)
    )
    session_record = session_query.scalar_one()
    success_segment = ContentSegment(
        key="skills",
        label="技能聚焦",
        sequence=3,
        status="success",
        original_text="React",
        suggested_text="React",
        markdown="React",
        explanation=SegmentExplanation(
            what="保留技能",
            why="已有证据",
            value="便于招聘方定位核心技术栈",
        ),
    )
    session_record.draft_sections_json = {"skills": success_segment.model_dump(mode="json")}
    session_record.diagnosis_json = TaskState(
        status="failed",
        phase="failed",
        message="生成失败，可重试。",
    ).model_dump(mode="json")
    session_record.status = "failed"
    db_session.add(session_record)
    await db_session.commit()

    response = await client.post(
        f"/tailored-resumes/workflows/{session_id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    retried = response.json()["data"]
    assert retried["tailored_resume"]["task_state"]["status"] == "processing"
    skills_segment = next(
        segment for segment in retried["tailored_resume"]["segments"] if segment["key"] == "skills"
    )
    assert skills_segment["status"] == "success"

    response = await client.post(
        f"/tailored-resumes/workflows/{session_id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_type": "workflow_page_exit", "payload": {"source": "test"}},
    )
    assert response.status_code == 200
    db_session.expire_all()

    session_query = await db_session.execute(
        select(ResumeOptimizationSession).where(ResumeOptimizationSession.id == session_id)
    )
    session_record = session_query.scalar_one()
    assert session_record.diagnosis_json["events"][-1]["event_type"] == "workflow_page_exit"


async def test_tailored_resume_success_rebuilds_segments_from_final_artifacts_not_stale_drafts(
    app, client, db_session
):
    user, token = await create_test_user(db_session, email="tailored-final-segments@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="final-segments")

    report = _build_match_report(user_id=user.id, resume=resume, job=job)
    db_session.add(report)
    await db_session.flush()

    optimized_resume = ResumeStructuredData.model_validate(resume.structured_json)
    optimized_resume.basic_info.summary = "聚焦 React 组件体系建设与复杂前端交付。"
    optimized_resume.work_experience_items[0].bullets[0].text = "主导后台管理系统重构，沉淀可复用组件体系。"

    session_record = ResumeOptimizationSession(
        user_id=user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        source_resume_version=resume.latest_version,
        source_job_version=job.latest_version,
        status="success",
        optimized_resume_json=optimized_resume.model_dump(mode="json"),
        tailored_resume_json=TailoredResumeDocument(summary=optimized_resume.basic_info.summary).model_dump(
            mode="json"
        ),
        tailored_resume_md="# Tailored Resume\n\n## Summary\n- rebuilt from final artifacts",
        draft_sections_json={
            "summary": ContentSegment(
                key="summary",
                label="职业摘要",
                sequence=1,
                status="success",
                original_text="旧预览原文",
                suggested_text="旧预览建议",
                markdown="旧预览建议",
                explanation=SegmentExplanation(
                    what="旧模板说明",
                    why="旧模板原因",
                    value="旧模板价值",
                ),
            ).model_dump(mode="json")
        },
        audit_report_json={
            "change_items": [
                {
                    "id": "summary_1",
                    "segment_key": "summary",
                    "section_label": "职业摘要",
                    "item_label": "摘要",
                    "change_type": "rewrite",
                    "before_text": "负责复杂前端项目交付与组件体系建设。",
                    "after_text": "聚焦 React 组件体系建设与复杂前端交付。",
                    "why": "在不新增事实的前提下，调整表达以更贴近岗位职责和关键词。",
                    "suggestion": "改写职业摘要的措辞，但不要新增无法证明的事实。",
                    "evidence": ["React"],
                }
            ]
        },
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(session_record)
    await db_session.commit()

    response = await client.get(
        f"/tailored-resumes/workflows/{session_record.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    workflow = response.json()["data"]
    segments_by_key = {
        segment["key"]: segment for segment in workflow["tailored_resume"]["segments"]
    }
    assert len(workflow["tailored_resume"]["segments"]) == 6
    assert segments_by_key["summary"]["original_text"] == "负责复杂前端项目交付与组件体系建设。"
    assert segments_by_key["summary"]["suggested_text"] == "聚焦 React 组件体系建设与复杂前端交付。"
    assert segments_by_key["summary"]["explanation"]["what"] != "旧模板说明"
    assert segments_by_key["summary"]["explanation"]["value"] == "让招聘方更快在职业摘要中看到 React 等相关证据。"


async def test_job_parse_success_autostarts_tailored_resume_for_recommended_resume(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr(
        "app.services.tailored_resume_autostart.schedule_tailored_resume_generation",
        lambda *args, **kwargs: None,
    )

    user, token = await create_test_user(db_session, email="tailored-autostart-job@example.com")
    resume, _ = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="autostart-job")

    response = await client.post(
        "/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Platform Engineer",
            "jd_text": "Need Python APIs, SQLAlchemy, background jobs and ownership.",
            "recommended_resume_id": str(resume.id),
        },
    )
    assert response.status_code == 201
    created_job = response.json()["data"]
    assert created_job["recommended_resume_id"] == str(resume.id)

    await process_job_parse_job(
        job_id=UUID(created_job["id"]),
        parse_job_id=UUID(created_job["latest_parse_job"]["id"]),
        session_factory=app.state.session_factory,
    )

    workflow = await maybe_autostart_tailored_resume_for_job(
        app,
        job_id=UUID(created_job["id"]),
    )
    assert workflow is not None
    assert workflow.resume.id == resume.id
    assert workflow.target_job.id == UUID(created_job["id"])
    assert workflow.tailored_resume.display_status == "processing"

    result = await db_session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.resume_id == resume.id,
            ResumeOptimizationSession.jd_id == UUID(created_job["id"]),
        )
    )
    sessions = list(result.scalars().all())
    assert len(sessions) == 1


async def test_resume_save_autostarts_only_for_trigger_job(app, client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.tailored_resume_autostart.schedule_tailored_resume_generation",
        lambda *args, **kwargs: None,
    )

    user, token = await create_test_user(db_session, email="tailored-autostart-resume@example.com")
    resume, job_a = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="resume-a")
    job_b = await _seed_ready_job(db_session, user=user, suffix="resume-b")

    response = await client.put(
        f"/resumes/{resume.id}/structured",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "markdown": "# Resume\n\n## Summary\n- refreshed content",
            "trigger_job_id": str(job_a.id),
        },
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.resume_id == resume.id,
        )
    )
    sessions = list(result.scalars().all())
    assert len(sessions) == 1
    assert sessions[0].jd_id == job_a.id
    assert sessions[0].status == "processing"
    assert sessions[0].source_resume_version == 2

    workflow_b = await maybe_autostart_tailored_resume(
        app,
        user_id=user.id,
        resume_id=resume.id,
        job_id=job_b.id,
    )
    assert workflow_b is not None

    result = await db_session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.resume_id == resume.id,
        )
    )
    sessions = list(result.scalars().all())
    assert len(sessions) == 2


async def test_autostart_reuses_existing_fresh_success_workflow(app, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.tailored_resume_autostart.schedule_tailored_resume_generation",
        lambda *args, **kwargs: None,
    )

    async def fake_request_json_completion(*, config, instructions, payload, max_tokens=4000):
        del config, instructions, payload, max_tokens
        return _fake_rewrite_response()

    monkeypatch.setattr(tailored_resume_service, "request_json_completion", fake_request_json_completion)

    user, _token = await create_test_user(db_session, email="tailored-autostart-idempotent@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="idempotent")

    first_workflow = await maybe_autostart_tailored_resume(
        app,
        user_id=user.id,
        resume_id=resume.id,
        job_id=job.id,
    )
    assert first_workflow is not None

    await tailored_resume_service.process_tailored_resume_workflow(
        session_id=first_workflow.tailored_resume.session_id,
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    second_workflow = await maybe_autostart_tailored_resume(
        app,
        user_id=user.id,
        resume_id=resume.id,
        job_id=job.id,
    )
    assert second_workflow is not None
    assert second_workflow.tailored_resume.session_id == first_workflow.tailored_resume.session_id
    assert second_workflow.tailored_resume.display_status == "success"

    result = await db_session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.resume_id == resume.id,
            ResumeOptimizationSession.jd_id == job.id,
        )
    )
    sessions = list(result.scalars().all())
    assert len(sessions) == 1
