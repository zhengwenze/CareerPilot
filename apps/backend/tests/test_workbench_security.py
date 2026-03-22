from __future__ import annotations

from app.models import JobDescription, MatchReport, Resume, ResumeOptimizationSession

from conftest import create_test_user


async def test_resume_and_job_lists_are_scoped_to_current_user(client, db_session, pdf_bytes):
    _, token_a = await create_test_user(db_session, email="a@example.com")
    _, token_b = await create_test_user(db_session, email="b@example.com")

    response = await client.post(
        "/resumes/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("resume-a.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201

    response = await client.post(
        "/jobs",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"title": "Frontend Lead", "jd_text": "Need React and leadership"},
    )
    assert response.status_code == 201
    job_id = response.json()["data"]["id"]

    response = await client.get("/resumes", headers={"Authorization": f"Bearer {token_a}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

    response = await client.get("/resumes", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 200
    assert response.json()["data"] == []

    response = await client.get("/jobs", headers={"Authorization": f"Bearer {token_a}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

    response = await client.get("/jobs", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 200
    assert response.json()["data"] == []

    response = await client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


async def test_tailored_resume_workflows_are_scoped_to_current_user(client, db_session):
    user_a, token_a = await create_test_user(db_session, email="workflow-a@example.com")
    user_b, token_b = await create_test_user(db_session, email="workflow-b@example.com")

    resume = Resume(
        user_id=user_a.id,
        file_name="resume.pdf",
        file_url="https://example.test/resume.pdf",
        storage_bucket="test",
        storage_object_key="resume.pdf",
        content_type="application/pdf",
        file_size=123,
        parse_status="success",
        raw_text="# Resume",
        structured_json={},
        parse_artifacts_json={"canonical_resume_md": "# Resume"},
        created_by=user_a.id,
        updated_by=user_a.id,
    )
    job = JobDescription(
        user_id=user_a.id,
        title="Frontend Lead",
        jd_text="Need React and leadership",
        latest_version=1,
        priority=3,
        status_stage="interview_ready",
        parse_status="success",
        structured_json={},
        competency_graph_json={},
        created_by=user_a.id,
        updated_by=user_a.id,
    )
    db_session.add_all([resume, job])
    await db_session.flush()
    report = MatchReport(
        user_id=user_a.id,
        resume_id=resume.id,
        jd_id=job.id,
        resume_version=1,
        job_version=1,
        status="success",
        fit_band="strong",
        stale_status="fresh",
        overall_score="88.00",
        rule_score="88.00",
        model_score="88.00",
        created_by=user_a.id,
        updated_by=user_a.id,
    )
    db_session.add(report)
    await db_session.flush()
    workflow = ResumeOptimizationSession(
        user_id=user_a.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        source_resume_version=1,
        source_job_version=1,
        status="ready",
        tailored_resume_json={"document": {}},
        tailored_resume_md="# Tailored Resume",
        created_by=user_a.id,
        updated_by=user_a.id,
    )
    db_session.add(workflow)
    await db_session.commit()

    response = await client.get(
        "/tailored-resumes/workflows",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

    response = await client.get(
        "/tailored-resumes/workflows",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == []

    response = await client.get(
        f"/tailored-resumes/workflows/{workflow.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404
