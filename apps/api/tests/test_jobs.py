from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.models import JobDescription, MatchReport, Resume


async def register_user(client, *, email: str, nickname: str) -> str:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "super-secret-123",
            "nickname": nickname,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_jobs_crud_flow(client, session_factory) -> None:
    access_token = await register_user(
        client,
        email="jobs@example.com",
        nickname="Job User",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    create_response = await client.post(
        "/jobs",
        headers=auth_headers,
        json={
            "title": "数据分析师",
            "company": "CareerPilot",
            "job_city": "上海",
            "employment_type": "全职",
            "source_name": "Boss直聘",
            "source_url": "https://example.com/jobs/1",
            "jd_text": "负责数据分析、SQL 建模和报表建设。",
        },
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()["data"]
    job_id = UUID(create_payload["id"])
    assert create_payload["parse_status"] == "pending"
    assert create_payload["structured_json"] is None

    list_response = await client.get("/jobs", headers=auth_headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()["data"]
    assert len(list_payload) == 1
    assert list_payload[0]["id"] == str(job_id)

    detail_response = await client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["title"] == "数据分析师"

    async with session_factory() as session:
        job = await session.get(JobDescription, job_id)
        assert job is not None
        job.parse_status = "success"
        job.parse_error = None
        job.structured_json = {
            "basic": {"title": "数据分析师"},
            "requirements": {"required_skills": ["SQL"]},
            "responsibilities": [],
            "benefits": [],
            "raw_summary": "已有结构化结果",
        }
        session.add(job)
        await session.commit()

    update_response = await client.put(
        f"/jobs/{job_id}",
        headers=auth_headers,
        json={
            "title": "高级数据分析师",
            "company": None,
            "jd_text": "负责数据分析、SQL 建模、实验分析与指标体系建设。",
        },
    )
    assert update_response.status_code == 200
    update_payload = update_response.json()["data"]
    assert update_payload["title"] == "高级数据分析师"
    assert update_payload["company"] is None
    assert update_payload["parse_status"] == "pending"
    assert update_payload["structured_json"] is None

    delete_response = await client.delete(f"/jobs/{job_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["message"] == "Job description deleted successfully"

    empty_list_response = await client.get("/jobs", headers=auth_headers)
    assert empty_list_response.status_code == 200
    assert empty_list_response.json()["data"] == []


@pytest.mark.asyncio
async def test_job_detail_is_scoped_to_current_user(client) -> None:
    first_token = await register_user(
        client,
        email="jobs-owner@example.com",
        nickname="Owner",
    )
    second_token = await register_user(
        client,
        email="jobs-other@example.com",
        nickname="Other",
    )

    first_headers = {"Authorization": f"Bearer {first_token}"}
    second_headers = {"Authorization": f"Bearer {second_token}"}

    create_response = await client.post(
        "/jobs",
        headers=first_headers,
        json={
            "title": "后端工程师",
            "jd_text": "负责 Python API 开发。",
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["data"]["id"]

    detail_response = await client.get(f"/jobs/{job_id}", headers=second_headers)
    assert detail_response.status_code == 404
    assert detail_response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_job_conflicts_when_match_report_exists(client, session_factory) -> None:
    access_token = await register_user(
        client,
        email="jobs-conflict@example.com",
        nickname="Conflict User",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    create_response = await client.post(
        "/jobs",
        headers=auth_headers,
        json={
            "title": "算法工程师",
            "jd_text": "负责模型训练与上线。",
        },
    )
    assert create_response.status_code == 201
    job_payload = create_response.json()["data"]
    job_id = UUID(job_payload["id"])
    user_id = UUID(job_payload["user_id"])

    resume_id = uuid4()
    report_id = uuid4()
    async with session_factory() as session:
        resume = Resume(
            id=resume_id,
            user_id=user_id,
            file_name="resume.pdf",
            file_url="minio://career-pilot-resumes/test/resume.pdf",
            storage_bucket="career-pilot-resumes",
            storage_object_key=f"resumes/{user_id}/{resume_id}/resume.pdf",
            content_type="application/pdf",
            file_size=1024,
            parse_status="success",
            latest_version=1,
            created_by=user_id,
            updated_by=user_id,
        )
        report = MatchReport(
            id=report_id,
            user_id=user_id,
            resume_id=resume.id,
            jd_id=job_id,
            status="success",
            overall_score=Decimal("88.00"),
            rule_score=Decimal("88.00"),
            model_score=Decimal("0.00"),
            dimension_scores_json={"required_skills": 36},
            gap_json={"strengths": [], "gaps": [], "actions": []},
            evidence_json={"matched_resume_fields": {}},
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(resume)
        session.add(report)
        await session.commit()

    delete_response = await client.delete(f"/jobs/{job_id}", headers=auth_headers)
    assert delete_response.status_code == 409
    assert delete_response.json()["error"]["code"] == "CONFLICT"
