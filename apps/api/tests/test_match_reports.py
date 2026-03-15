from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.models import JobDescription, MatchReport, Resume


async def register_user(client, *, email: str, nickname: str) -> tuple[str, UUID]:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "super-secret-123",
            "nickname": nickname,
        },
    )
    assert response.status_code == 201
    payload = response.json()["data"]
    return payload["access_token"], UUID(payload["user"]["id"])


async def create_match_report_fixture(*, session_factory, user_id: UUID) -> tuple[str, str]:
    resume_id = uuid4()
    job_id = uuid4()
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
            raw_text=(
                "张三\n"
                "zhangsan@example.com 13800138000 上海\n"
                "教育背景\n复旦大学 统计学 本科\n"
                "工作经历\n2023.01-至今 CareerPilot 数据分析师\n"
                "负责 SQL、Python、指标体系与实验分析。\n"
                "项目经历\n增长分析平台重构\n"
                "技能\nPython SQL Tableau English"
            ),
            structured_json={
                "basic_info": {
                    "name": "张三",
                    "email": "zhangsan@example.com",
                    "phone": "13800138000",
                    "location": "上海",
                    "summary": "负责增长分析和实验分析。",
                },
                "education": ["复旦大学 统计学 本科"],
                "work_experience": ["2023.01-至今 CareerPilot 数据分析师"],
                "projects": ["增长分析平台重构"],
                "skills": {
                    "technical": ["Python", "SQL", "Tableau", "数据分析", "实验分析"],
                    "tools": [],
                    "languages": ["English"],
                },
                "certifications": [],
            },
            latest_version=1,
            created_by=user_id,
            updated_by=user_id,
        )
        job = JobDescription(
            id=job_id,
            user_id=user_id,
            title="高级数据分析师",
            company="CareerPilot",
            jd_text="负责 SQL、Python 与实验分析。",
            parse_status="success",
            structured_json={"basic": {"title": "高级数据分析师"}},
            created_by=user_id,
            updated_by=user_id,
        )
        report = MatchReport(
            id=report_id,
            user_id=user_id,
            resume_id=resume_id,
            jd_id=job_id,
            status="success",
            overall_score=Decimal("82.50"),
            rule_score=Decimal("82.50"),
            model_score=Decimal("0.00"),
            dimension_scores_json={"required_skills": 32, "preferred_skills": 10},
            gap_json={"strengths": [{"label": "Python"}], "gaps": [], "actions": []},
            evidence_json={"matched_resume_fields": {"skills": ["Python", "SQL"]}},
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(resume)
        session.add(job)
        session.add(report)
        await session.commit()

    return str(job_id), str(report_id)


@pytest.mark.asyncio
async def test_match_report_list_detail_and_delete(client, session_factory) -> None:
    access_token, user_id = await register_user(
        client,
        email="match-owner@example.com",
        nickname="Match Owner",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    job_id, report_id = await create_match_report_fixture(
        session_factory=session_factory,
        user_id=user_id,
    )

    list_response = await client.get(
        f"/jobs/{job_id}/match-reports",
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()["data"]
    assert len(list_payload) == 1
    assert list_payload[0]["id"] == report_id

    detail_response = await client.get(
        f"/match-reports/{report_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["data"]
    assert detail_payload["id"] == report_id
    assert detail_payload["overall_score"] == "82.50"

    delete_response = await client.delete(
        f"/match-reports/{report_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["message"] == "Match report deleted successfully"

    next_list_response = await client.get(
        f"/jobs/{job_id}/match-reports",
        headers=auth_headers,
    )
    assert next_list_response.status_code == 200
    assert next_list_response.json()["data"] == []


@pytest.mark.asyncio
async def test_create_match_report_endpoint_generates_report(client, session_factory) -> None:
    access_token, user_id = await register_user(
        client,
        email="match-create@example.com",
        nickname="Match Create",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    create_response = await client.post(
        "/jobs",
        headers=auth_headers,
        json={
            "title": "高级数据分析师",
            "company": "CareerPilot",
            "job_city": "上海",
            "employment_type": "全职",
            "jd_text": (
                "岗位职责\n"
                "1. 负责指标体系建设和实验分析。\n"
                "2. 与产品和运营协作推进增长项目。\n"
                "任职要求\n"
                "1. 熟悉 Python、SQL、Tableau。\n"
                "2. 3年以上数据分析经验，本科及以上。"
            ),
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["data"]["id"]

    resume_id = uuid4()
    async with session_factory() as session:
        resume = Resume(
            id=resume_id,
            user_id=user_id,
            file_name="candidate.pdf",
            file_url="minio://career-pilot-resumes/test/candidate.pdf",
            storage_bucket="career-pilot-resumes",
            storage_object_key=f"resumes/{user_id}/{resume_id}/candidate.pdf",
            content_type="application/pdf",
            file_size=1024,
            parse_status="success",
            raw_text=(
                "李四\n"
                "lisi@example.com 13800138001 上海\n"
                "教育背景\n上海交通大学 本科\n"
                "工作经历\n2022.01-至今 CareerPilot 数据分析师\n"
                "负责 Python、SQL、Tableau、指标体系和实验分析。\n"
                "项目经历\n增长实验平台\n"
                "设计看板并复盘 A/B Testing 结果。"
            ),
            structured_json={
                "basic_info": {
                    "name": "李四",
                    "email": "lisi@example.com",
                    "phone": "13800138001",
                    "location": "上海",
                    "summary": "负责增长分析、实验分析和数据建模。",
                },
                "education": ["上海交通大学 本科"],
                "work_experience": ["2022.01-至今 CareerPilot 数据分析师"],
                "projects": ["增长实验平台"],
                "skills": {
                    "technical": ["Python", "SQL", "Tableau", "A/B Testing", "实验分析"],
                    "tools": [],
                    "languages": [],
                },
                "certifications": [],
            },
            latest_version=1,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(resume)
        await session.commit()

    report_response = await client.post(
        f"/jobs/{job_id}/match-reports",
        headers=auth_headers,
        json={
            "resume_id": str(resume_id),
            "force_refresh": True,
        },
    )
    assert report_response.status_code == 200
    payload = report_response.json()["data"]
    assert payload["status"] == "success"
    assert payload["rule_score"] != "0.00"
    assert "required_skills" in payload["dimension_scores_json"]
    assert "ai_correction_delta" in payload["dimension_scores_json"]
    assert payload["gap_json"]["actions"]

    list_response = await client.get(
        f"/jobs/{job_id}/match-reports",
        headers=auth_headers,
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1


@pytest.mark.asyncio
async def test_match_report_detail_is_scoped_to_current_user(client, session_factory) -> None:
    owner_token, owner_id = await register_user(
        client,
        email="match-owner-2@example.com",
        nickname="Match Owner 2",
    )
    other_token, _ = await register_user(
        client,
        email="match-other@example.com",
        nickname="Match Other",
    )
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    _, report_id = await create_match_report_fixture(
        session_factory=session_factory,
        user_id=owner_id,
    )

    owner_detail = await client.get(f"/match-reports/{report_id}", headers=owner_headers)
    assert owner_detail.status_code == 200

    other_detail = await client.get(f"/match-reports/{report_id}", headers=other_headers)
    assert other_detail.status_code == 404
    assert other_detail.json()["error"]["code"] == "NOT_FOUND"
