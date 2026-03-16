from __future__ import annotations

import io
import re
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.models import Resume, ResumeParseJob
from app.services.resume import process_resume_parse_job


def build_pdf_bytes() -> bytes:
    objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n",
        (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\n"
            "endobj\n"
        ),
        (
            "4 0 obj\n"
            "<< /Length 216 >>\n"
            "stream\n"
            "BT\n"
            "/F1 12 Tf\n"
            "36 250 Td\n"
            "(John Doe) Tj\n"
            "0 -18 Td\n"
            "(john@example.com 13800138000 Shanghai) Tj\n"
            "0 -18 Td\n"
            "(Education) Tj\n"
            "0 -18 Td\n"
            "(Fudan University - Computer Science) Tj\n"
            "0 -18 Td\n"
            "(Experience) Tj\n"
            "0 -18 Td\n"
            "(CareerPilot - Frontend Intern) Tj\n"
            "0 -18 Td\n"
            "(Projects) Tj\n"
            "0 -18 Td\n"
            "(Resume Platform Reconstruction) Tj\n"
            "0 -18 Td\n"
            "(Skills) Tj\n"
            "0 -18 Td\n"
            "(Python React Docker English) Tj\n"
            "ET\n"
            "endstream\n"
            "endobj\n"
        ),
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(buffer.tell())
        buffer.write(obj.encode("utf-8"))

    xref_offset = buffer.tell()
    buffer.write(f"xref\n0 {len(offsets)}\n".encode())
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode())
    buffer.write(
        (
            "trailer\n"
            f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n"
            "%%EOF"
        ).encode()
    )
    return buffer.getvalue()


async def wait_for_resume_success(
    client,
    *,
    resume_id: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    for _ in range(8):
        detail_response = await client.get(f"/resumes/{resume_id}", headers=headers)
        assert detail_response.status_code == 200
        payload = detail_response.json()["data"]
        if payload["parse_status"] == "success":
            return payload
    raise AssertionError("resume parse did not complete in time")


@pytest.mark.asyncio
async def test_resume_upload_list_detail_and_download_url(client) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "resume@example.com",
            "password": "super-secret-123",
            "nickname": "Resume User",
        },
    )
    access_token = register_response.json()["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    upload_response = await client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.pdf", build_pdf_bytes(), "application/pdf")},
    )

    assert upload_response.status_code == 201
    upload_payload = upload_response.json()["data"]
    assert upload_payload["file_name"] == "resume.pdf"
    assert upload_payload["parse_status"] in {"pending", "processing", "success"}
    assert upload_payload["file_url"].startswith("minio://career-pilot-resumes/")

    resume_id = upload_payload["id"]

    list_response = await client.get("/resumes", headers=auth_headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()["data"]
    assert len(list_payload) == 1
    assert list_payload[0]["id"] == resume_id

    detail_payload = await wait_for_resume_success(
        client,
        resume_id=resume_id,
        headers=auth_headers,
    )
    assert detail_payload["id"] == resume_id
    assert detail_payload["storage_bucket"] == "career-pilot-resumes"
    assert detail_payload["raw_text"]
    assert detail_payload["structured_json"]["basic_info"]["email"] == "john@example.com"
    assert "Python" in detail_payload["structured_json"]["skills"]["technical"]

    download_response = await client.get(
        f"/resumes/{resume_id}/download-url",
        headers=auth_headers,
    )
    assert download_response.status_code == 200
    download_payload = download_response.json()["data"]
    assert "https://fake-storage.local/career-pilot-resumes/" in download_payload["download_url"]
    assert download_payload["expires_in"] == 3600

    parse_jobs_response = await client.get(
        f"/resumes/{resume_id}/parse-jobs",
        headers=auth_headers,
    )
    assert parse_jobs_response.status_code == 200
    parse_jobs_payload = parse_jobs_response.json()["data"]
    assert parse_jobs_payload[0]["status"] == "success"

    structured_update_response = await client.put(
        f"/resumes/{resume_id}/structured",
        headers=auth_headers,
        json={
            "structured_json": {
                "basic_info": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "13800138000",
                    "location": "Shanghai",
                    "summary": "Updated summary",
                },
                "education": ["Fudan University - Computer Science"],
                "work_experience": ["CareerPilot - Frontend Intern"],
                "projects": ["Resume Platform Reconstruction"],
                "skills": {
                    "technical": ["Python", "React"],
                    "tools": ["Docker"],
                    "languages": ["English"],
                },
                "certifications": [],
            }
        },
    )
    assert structured_update_response.status_code == 200
    assert (
        structured_update_response.json()["data"]["structured_json"]["basic_info"]["summary"]
        == "Updated summary"
    )

    retry_parse_response = await client.post(
        f"/resumes/{resume_id}/parse",
        headers=auth_headers,
    )
    assert retry_parse_response.status_code == 200


@pytest.mark.asyncio
async def test_resume_detail_reschedules_pending_parse_job(client, app, session_factory) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "resume-reschedule@example.com",
            "password": "super-secret-123",
            "nickname": "Resume Reschedule",
        },
    )
    access_token = register_response.json()["data"]["access_token"]
    user_id = UUID(register_response.json()["data"]["user"]["id"])
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    resume_id = uuid4()
    parse_job_id = uuid4()
    object_key = f"resumes/{user_id}/{resume_id}/resume.pdf"
    fake_storage = app.state.object_storage
    fake_storage.objects[("career-pilot-resumes", object_key)] = build_pdf_bytes()
    app.state.resume_parse_tasks = set()
    app.state.resume_parse_task_ids = set()

    async with session_factory() as session:
        session.add(
            Resume(
                id=resume_id,
                user_id=user_id,
                file_name="resume.pdf",
                file_url=f"minio://career-pilot-resumes/{object_key}",
                storage_bucket="career-pilot-resumes",
                storage_object_key=object_key,
                content_type="application/pdf",
                file_size=len(fake_storage.objects[("career-pilot-resumes", object_key)]),
                parse_status="pending",
                created_by=user_id,
                updated_by=user_id,
            )
        )
        session.add(
            ResumeParseJob(
                id=parse_job_id,
                resume_id=resume_id,
                status="pending",
                attempt_count=0,
                created_by=user_id,
                updated_by=user_id,
            )
        )
        await session.commit()

    detail_response = await client.get(f"/resumes/{resume_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["parse_status"] in {"pending", "processing"}

    detail_payload = await wait_for_resume_success(
        client,
        resume_id=str(resume_id),
        headers=auth_headers,
    )
    assert detail_payload["structured_json"]["basic_info"]["email"] == "john@example.com"


@pytest.mark.asyncio
async def test_process_resume_parse_job_persists_naive_timestamps(session_factory, app) -> None:
    user_id = uuid4()
    resume_id = uuid4()
    parse_job_id = uuid4()
    object_key = f"resumes/{user_id}/{resume_id}/resume.pdf"
    fake_storage = app.state.object_storage
    pdf_bytes = build_pdf_bytes()
    fake_storage.objects[("career-pilot-resumes", object_key)] = pdf_bytes

    async with session_factory() as session:
        session.add(
            Resume(
                id=resume_id,
                user_id=user_id,
                file_name="resume.pdf",
                file_url=f"minio://career-pilot-resumes/{object_key}",
                storage_bucket="career-pilot-resumes",
                storage_object_key=object_key,
                content_type="application/pdf",
                file_size=len(pdf_bytes),
                parse_status="pending",
                created_by=user_id,
                updated_by=user_id,
            )
        )
        session.add(
            ResumeParseJob(
                id=parse_job_id,
                resume_id=resume_id,
                status="pending",
                attempt_count=0,
                created_by=user_id,
                updated_by=user_id,
            )
        )
        await session.commit()

    await process_resume_parse_job(
        resume_id=resume_id,
        parse_job_id=parse_job_id,
        storage=fake_storage,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        resume = await session.get(Resume, resume_id)
        parse_job = await session.get(ResumeParseJob, parse_job_id)

    assert resume is not None
    assert parse_job is not None
    assert resume.parse_status == "success"
    assert parse_job.status == "success"
    assert parse_job.started_at is not None and parse_job.started_at.tzinfo is None
    assert parse_job.finished_at is not None and parse_job.finished_at.tzinfo is None


@pytest.mark.asyncio
async def test_resume_upload_rejects_non_pdf(client) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "resume-invalid@example.com",
            "password": "super-secret-123",
            "nickname": "Resume Invalid",
        },
    )
    access_token = register_response.json()["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    upload_response = await client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.txt", b"plain text", "text/plain")},
    )

    assert upload_response.status_code == 400
    assert upload_response.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_resume_upload_accepts_unicode_pdf_filename(client) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "resume-unicode@example.com",
            "password": "super-secret-123",
            "nickname": "Resume Unicode",
        },
    )
    access_token = register_response.json()["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    upload_response = await client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("郑文泽简历.pdf", build_pdf_bytes(), "application/pdf")},
    )

    assert upload_response.status_code == 201
    file_name = upload_response.json()["data"]["file_name"]
    assert re.fullmatch(r"resume-[0-9a-f]{32}\.pdf", file_name)


@pytest.mark.asyncio
async def test_resume_delete_removes_record_and_storage(client, app) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "resume-delete@example.com",
            "password": "super-secret-123",
            "nickname": "Resume Delete",
        },
    )
    access_token = register_response.json()["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    upload_response = await client.post(
        "/resumes/upload",
        headers=auth_headers,
        files={"file": ("resume.pdf", build_pdf_bytes(), "application/pdf")},
    )

    assert upload_response.status_code == 201
    upload_payload = upload_response.json()["data"]
    resume_id = upload_payload["id"]
    storage_bucket = upload_payload["storage_bucket"]
    storage_object_key = upload_payload["storage_object_key"]

    delete_response = await client.delete(
        f"/resumes/{resume_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["message"] == "Resume deleted successfully"

    list_response = await client.get("/resumes", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.json()["data"] == []

    detail_response = await client.get(f"/resumes/{resume_id}", headers=auth_headers)
    assert detail_response.status_code == 404
    assert detail_response.json()["error"]["code"] == "NOT_FOUND"

    fake_storage = app.state.object_storage
    assert (storage_bucket, storage_object_key) not in fake_storage.objects
