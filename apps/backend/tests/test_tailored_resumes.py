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
    assert len(workflow["tailored_resume"]["segments"]) == 5
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
    assert len(completed["tailored_resume"]["segments"]) == 5
    assert completed["tailored_resume"]["downloadable"] is True
    assert completed["tailored_resume"]["retryable"] is False
    assert all(
        segment["explanation"]["what"] for segment in completed["tailored_resume"]["segments"]
    )


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
    assert len(listed["tailored_resume"]["segments"]) == 5


async def test_tailored_resume_scheduler_updates_workflow_progress_and_completes(
    app, client, db_session, monkeypatch
):
    user, token = await create_test_user(db_session, email="tailored-scheduler@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="scheduler")

    async def fake_generate_rewrite_projection(*, source_resume, job, report, settings):
        del job, report, settings
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
        sequence=2,
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
