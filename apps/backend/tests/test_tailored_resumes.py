from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models import JobDescription, Resume, ResumeOptimizationSession
from app.schemas.ai_runtime import ContentSegment, SegmentExplanation, TaskState
from app.schemas.resume import (
    ResumeBasicInfo,
    ResumeExperienceBullet,
    ResumeProjectItem,
    ResumeStructuredData,
    ResumeWorkExperienceItem,
)
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


async def test_tailored_resume_optimize_returns_processing_then_persists_segments(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.tailored_resumes.schedule_tailored_resume_generation", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="tailored@example.com")
    resume, job = await _seed_tailored_resume_dependencies(db_session, user=user, suffix="demo")

    async def fake_request_json_completion(*, config, instructions, payload, max_tokens=4000):
        del config, instructions, payload, max_tokens
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
    assert len(workflow["tailored_resume"]["segments"]) == 5

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
    assert completed["tailored_resume"]["document"]["markdown"]
    assert len(completed["tailored_resume"]["segments"]) == 5
    assert all(
        segment["explanation"]["what"] for segment in completed["tailored_resume"]["segments"]
    )


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
