from __future__ import annotations

from uuid import UUID

from app.models import JobDescription

from conftest import create_test_user


async def test_update_job_persists_latest_jd_to_database(client, db_session):
    _, token = await create_test_user(db_session, email="job-update@example.com")

    create_response = await client.post(
        "/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Frontend Engineer",
            "company": "Career Pilot",
            "jd_text": "Build polished React interfaces.",
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["data"]["id"]

    update_payload = {
        "title": "Senior Frontend Engineer",
        "company": "Career Pilot",
        "job_city": "Shanghai",
        "jd_text": "Lead the React workspace, own JD-driven resume tailoring, and improve performance.",
    }
    update_response = await client.put(
        f"/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_payload,
    )

    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["title"] == update_payload["title"]
    assert updated["job_city"] == update_payload["job_city"]
    assert updated["jd_text"] == update_payload["jd_text"]
    assert updated["latest_version"] == 2
    assert updated["parse_status"] == "pending"

    persisted = await db_session.get(JobDescription, UUID(job_id))
    assert persisted is not None
    assert persisted.title == update_payload["title"]
    assert persisted.job_city == update_payload["job_city"]
    assert persisted.jd_text == update_payload["jd_text"]
    assert persisted.latest_version == 2
    assert persisted.parse_status == "pending"
