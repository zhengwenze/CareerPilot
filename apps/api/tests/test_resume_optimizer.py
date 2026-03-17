from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest

from app.models import MatchReport, Resume


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


async def wait_for_job_parse_success(client, *, job_id: str, auth_headers: dict[str, str]) -> dict:
    for _ in range(30):
        response = await client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()["data"]
        if payload["parse_status"] == "success":
            return payload
        await asyncio.sleep(0.05)
    raise AssertionError("job parse did not complete in time")


async def wait_for_match_report_success(
    client,
    *,
    report_id: str,
    auth_headers: dict[str, str],
) -> dict:
    for _ in range(30):
        response = await client.get(f"/match-reports/{report_id}", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()["data"]
        if payload["status"] == "success":
            return payload
        await asyncio.sleep(0.05)
    raise AssertionError("match report did not complete in time")


async def create_fresh_match_report(
    client,
    *,
    session_factory,
    auth_headers: dict[str, str],
    user_id: UUID,
) -> dict:
    create_job_response = await client.post(
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
    assert create_job_response.status_code == 201
    job_id = create_job_response.json()["data"]["id"]
    await wait_for_job_parse_success(client, job_id=job_id, auth_headers=auth_headers)

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
    report_id = report_response.json()["data"]["id"]
    report_payload = await wait_for_match_report_success(
        client,
        report_id=report_id,
        auth_headers=auth_headers,
    )
    return {
        "job_id": job_id,
        "resume_id": str(resume_id),
        "report_id": report_id,
        "report": report_payload,
    }


@pytest.mark.asyncio
async def test_create_and_reuse_resume_optimization_session(client, session_factory) -> None:
    access_token, user_id = await register_user(
        client,
        email="optimizer@example.com",
        nickname="Optimizer User",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    match_context = await create_fresh_match_report(
        client,
        session_factory=session_factory,
        auth_headers=auth_headers,
        user_id=user_id,
    )

    create_response = await client.post(
        "/resume-optimization-sessions",
        headers=auth_headers,
        json={"match_report_id": match_context["report_id"]},
    )
    assert create_response.status_code == 201
    payload = create_response.json()["data"]
    assert payload["status"] == "draft"
    assert payload["optimizer_context"]["job_title"] == "高级数据分析师"
    assert payload["selected_tasks"]

    reused_response = await client.post(
        "/resume-optimization-sessions",
        headers=auth_headers,
        json={"match_report_id": match_context["report_id"]},
    )
    assert reused_response.status_code == 201
    assert reused_response.json()["data"]["id"] == payload["id"]

    detail_response = await client.get(
        f"/resume-optimization-sessions/{payload['id']}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["data"]
    assert detail_payload["tailoring_plan_snapshot"]["rewrite_tasks"]


@pytest.mark.asyncio
async def test_create_resume_optimization_session_rejects_stale_report(
    client,
    session_factory,
) -> None:
    access_token, user_id = await register_user(
        client,
        email="optimizer-stale@example.com",
        nickname="Optimizer Stale",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    match_context = await create_fresh_match_report(
        client,
        session_factory=session_factory,
        auth_headers=auth_headers,
        user_id=user_id,
    )

    async with session_factory() as session:
        report = await session.get(MatchReport, UUID(match_context["report_id"]))
        assert report is not None
        report.stale_status = "stale"
        session.add(report)
        await session.commit()

    create_response = await client.post(
        "/resume-optimization-sessions",
        headers=auth_headers,
        json={"match_report_id": match_context["report_id"]},
    )
    assert create_response.status_code == 409
    assert create_response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_generate_resume_optimization_suggestions_returns_rule_based_drafts(
    client,
    session_factory,
) -> None:
    access_token, user_id = await register_user(
        client,
        email="optimizer-rule@example.com",
        nickname="Optimizer Rule",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    match_context = await create_fresh_match_report(
        client,
        session_factory=session_factory,
        auth_headers=auth_headers,
        user_id=user_id,
    )

    create_response = await client.post(
        "/resume-optimization-sessions",
        headers=auth_headers,
        json={"match_report_id": match_context["report_id"]},
    )
    session_id = create_response.json()["data"]["id"]

    suggest_response = await client.post(
        f"/resume-optimization-sessions/{session_id}/suggestions",
        headers=auth_headers,
    )
    assert suggest_response.status_code == 200
    payload = suggest_response.json()["data"]
    assert payload["status"] == "ready"
    assert "求职方向聚焦" in payload["draft_sections"]["summary"]["suggested_text"]
    assert "核心指标" in payload["draft_sections"]["work_experience"]["suggested_text"]
    assert "项目名称｜" in payload["draft_sections"]["projects"]["suggested_text"]


@pytest.mark.asyncio
async def test_apply_resume_optimization_session_updates_resume_and_stales_report(
    client,
    session_factory,
) -> None:
    access_token, user_id = await register_user(
        client,
        email="optimizer-apply@example.com",
        nickname="Optimizer Apply",
    )
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    match_context = await create_fresh_match_report(
        client,
        session_factory=session_factory,
        auth_headers=auth_headers,
        user_id=user_id,
    )

    create_response = await client.post(
        "/resume-optimization-sessions",
        headers=auth_headers,
        json={"match_report_id": match_context["report_id"]},
    )
    session_id = create_response.json()["data"]["id"]

    suggest_response = await client.post(
        f"/resume-optimization-sessions/{session_id}/suggestions",
        headers=auth_headers,
    )
    assert suggest_response.status_code == 200

    apply_response = await client.post(
        f"/resume-optimization-sessions/{session_id}/apply",
        headers=auth_headers,
    )
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()["data"]
    assert apply_payload["applied_resume_version"] == 2

    resume_response = await client.get(
        f"/resumes/{match_context['resume_id']}",
        headers=auth_headers,
    )
    assert resume_response.status_code == 200
    resume_payload = resume_response.json()["data"]
    assert resume_payload["latest_version"] == 2
    assert resume_payload["structured_json"]["basic_info"]["summary"]

    report_response = await client.get(
        f"/match-reports/{match_context['report_id']}",
        headers=auth_headers,
    )
    assert report_response.status_code == 200
    assert report_response.json()["data"]["stale_status"] == "stale"
