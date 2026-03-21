from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ApiException
from app.core.config import Settings
from app.models import Resume, ResumeParseJob, User
from app.schemas.resume import ResumeStructuredData
from app.services.ai_client import AIClientError
from app.services.resume import process_resume_parse_job, validate_resume_upload


class FakeStorage:
    async def get_object_bytes(self, *, bucket_name: str, object_key: str) -> bytes:
        return b"%PDF-fake"


class AppliedAIProvider:
    async def correct(self, payload: object) -> SimpleNamespace:
        return SimpleNamespace(
            status="applied",
            structured_data=ResumeStructuredData(
                basic_info={
                    "name": "郑文泽",
                    "title": "AI 应用开发",
                    "status": "立即到岗",
                    "email": "zheng@example.com",
                    "phone": "17590522997",
                    "location": "北京",
                    "summary": "",
                },
                education_items=[
                    {
                        "school": "新疆大学",
                        "major": "软件工程",
                        "degree": "本科",
                        "start_date": "2023.09",
                        "end_date": "2027.06",
                        "honors": ["211", "双一流"],
                    }
                ],
                work_experience=[],
                project_items=[
                    {
                        "name": "黑马点评",
                        "role": "核心开发",
                        "summary": "高可用秒杀系统",
                        "bullets": [
                            {"text": "完成高可用秒杀系统从0到1的架构设计与实现"}
                        ],
                    }
                ],
                skills={
                    "technical": ["Python", "FastAPI"],
                    "tools": ["Docker"],
                    "languages": ["English"],
                },
                certifications=["百度之星金奖 竞赛"],
            ),
        )


class InvalidAIProvider:
    async def correct(self, payload: object) -> SimpleNamespace:
        raise AIClientError(
            category="invalid_response_format",
            detail="structured payload validation failed",
        )


@pytest.mark.asyncio
async def test_process_resume_parse_job_persists_success_with_applied_ai(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume, parse_job = await _create_resume_and_parse_job(db_session, test_user)

    monkeypatch.setattr(
        "app.services.resume.extract_text_from_resume_bytes",
        lambda **_kwargs: SimpleNamespace(
            raw_text=_raw_text(),
            source_type="pdf",
            ocr_used=False,
            ocr_engine="none",
        ),
    )
    monkeypatch.setattr(
        "app.services.resume.build_structured_resume",
        lambda _raw_text: _rule_structured_data(),
    )
    monkeypatch.setattr(
        "app.services.resume.build_resume_ai_correction_provider",
        lambda _settings: AppliedAIProvider(),
    )

    await process_resume_parse_job(
        resume_id=resume.id,
        parse_job_id=parse_job.id,
        storage=FakeStorage(),
        session_factory=session_factory,
        settings=Settings(),
    )

    async with session_factory() as session:
        persisted_resume = await session.get(Resume, resume.id)
        persisted_job = await session.get(ResumeParseJob, parse_job.id)

    assert persisted_resume is not None
    assert persisted_job is not None
    assert persisted_resume.parse_status == "success"
    assert persisted_resume.parse_error is None
    assert persisted_resume.structured_json is not None
    assert persisted_resume.structured_json["meta"]["schema_version"] == 2
    assert persisted_resume.structured_json["project_items"]
    assert persisted_resume.structured_json["certification_items"]
    assert persisted_resume.parse_artifacts_json["pipeline"]["current_stage"] == "completed"
    assert persisted_resume.parse_artifacts_json["meta"]["source_type"] == "pdf"
    assert persisted_resume.parse_artifacts_json["meta"]["ai_correction_applied"] is True
    assert persisted_resume.parse_artifacts_json["quality"]["text_extractable"] is True
    assert persisted_resume.parse_artifacts_json["canonical_resume_md"].startswith(
        "# 郑文泽"
    )
    assert "AI 应用开发｜立即到岗" in persisted_resume.parse_artifacts_json["canonical_resume_md"]
    assert "## 项目经历" in persisted_resume.parse_artifacts_json["canonical_resume_md"]
    assert "### 黑马点评｜核心开发" in persisted_resume.parse_artifacts_json["canonical_resume_md"]
    assert "- 完成高可用秒杀系统从0到1的架构设计与实现" in (
        persisted_resume.parse_artifacts_json["canonical_resume_md"]
    )
    assert persisted_resume.structured_json["projects"] == [
        "黑马点评 核心开发 高可用秒杀系统 完成高可用秒杀系统从0到1的架构设计与实现。"
    ]
    assert persisted_job.status == "success"
    assert persisted_job.ai_status == "applied"
    assert persisted_job.ai_message == "已完成校准"


@pytest.mark.asyncio
async def test_process_resume_parse_job_falls_back_to_rule_result_on_invalid_ai(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume, parse_job = await _create_resume_and_parse_job(db_session, test_user)
    rule_result = _rule_structured_data()

    monkeypatch.setattr(
        "app.services.resume.extract_text_from_resume_bytes",
        lambda **_kwargs: SimpleNamespace(
            raw_text=_raw_text(),
            source_type="pdf",
            ocr_used=False,
            ocr_engine="none",
        ),
    )
    monkeypatch.setattr(
        "app.services.resume.build_structured_resume",
        lambda _raw_text: rule_result,
    )
    monkeypatch.setattr(
        "app.services.resume.build_resume_ai_correction_provider",
        lambda _settings: InvalidAIProvider(),
    )

    await process_resume_parse_job(
        resume_id=resume.id,
        parse_job_id=parse_job.id,
        storage=FakeStorage(),
        session_factory=session_factory,
        settings=Settings(),
    )

    async with session_factory() as session:
        persisted_resume = await session.get(Resume, resume.id)
        persisted_job = await session.get(ResumeParseJob, parse_job.id)
        job_count = await session.scalar(select(func.count()).select_from(ResumeParseJob))

    assert persisted_resume is not None
    assert persisted_job is not None
    assert persisted_resume.parse_status == "success"
    assert persisted_resume.structured_json == rule_result.model_dump()
    assert persisted_resume.parse_artifacts_json["pipeline"]["current_stage"] == "completed"
    assert persisted_resume.parse_artifacts_json["meta"]["ai_correction_applied"] is False
    assert persisted_resume.parse_artifacts_json["canonical_resume_md"].startswith(
        "# 郑文泽"
    )
    assert "## 教育经历" in persisted_resume.parse_artifacts_json["canonical_resume_md"]
    assert any(
        item["status"] == "fallback"
        for item in persisted_resume.parse_artifacts_json["pipeline"]["history"]
        if item["stage"] == "ai_correction"
    )
    assert persisted_job.status == "success"
    assert persisted_job.ai_status == "fallback_rule"
    assert persisted_job.ai_message == "AI 校准失败，已回退规则解析（模型返回格式非法）"
    assert job_count == 1


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_validate_resume_upload_rejects_non_pdf_files(
) -> None:
    with pytest.raises(ApiException) as exc_info:
        await validate_resume_upload(
            UploadFile(
                file=BytesIO(b"fake docx"),
                filename="resume.docx",
                headers={"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
            ),
            settings=Settings(),
        )

    assert exc_info.value.message == "Only text-based PDF resumes are supported"


@pytest.mark.asyncio
async def test_validate_resume_upload_accepts_pdf_files() -> None:
    file_name, content_type, content = await validate_resume_upload(
        UploadFile(
            file=BytesIO(b"%PDF-1.4 fake"),
            filename="resume.pdf",
            headers={"content-type": "application/pdf"},
        ),
        settings=Settings(),
    )

    assert file_name == "resume.pdf"
    assert content_type == "application/pdf"
    assert content == b"%PDF-1.4 fake"


def _raw_text() -> str:
    return """
    郑文泽
    AI 应用开发 立即到岗
    zheng@example.com 17590522997 北京
    教育背景
    新疆大学 软件工程 本科 2023.09-2027.06 211 双一流
    项目经历
    黑马点评
    完成高可用秒杀系统从0到1的架构设计与实现
    证书奖项
    百度之星金奖
    """.strip()


def _rule_structured_data() -> ResumeStructuredData:
    return ResumeStructuredData(
        basic_info={
            "name": "郑文泽",
            "email": "zheng@example.com",
            "phone": "17590522997",
            "location": "北京",
            "summary": "",
        },
        education=["新疆大学 软件工程 本科 2023.09-2027.06 211 双一流"],
        work_experience=[],
        projects=["黑马点评 完成高可用秒杀系统从0到1的架构设计与实现"],
        skills={
            "technical": ["Python", "FastAPI"],
            "tools": ["Docker"],
            "languages": [],
        },
        certifications=["百度之星金奖"],
    )


async def _create_resume_and_parse_job(
    session: AsyncSession,
    user: User,
    *,
    file_name: str = "resume.pdf",
    content_type: str = "application/pdf",
) -> tuple[Resume, ResumeParseJob]:
    resume = Resume(
        id=uuid4(),
        user_id=user.id,
        file_name=file_name,
        file_url=f"minio://career-pilot/{file_name}",
        storage_bucket="career-pilot",
        storage_object_key=f"resumes/{user.id}/{file_name}",
        content_type=content_type,
        file_size=1024,
        parse_status="pending",
        parse_artifacts_json={},
        created_by=user.id,
        updated_by=user.id,
    )
    parse_job = ResumeParseJob(
        id=uuid4(),
        resume_id=resume.id,
        status="pending",
        attempt_count=0,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(resume)
    session.add(parse_job)
    await session.commit()
    await session.refresh(resume)
    await session.refresh(parse_job)
    return resume, parse_job
