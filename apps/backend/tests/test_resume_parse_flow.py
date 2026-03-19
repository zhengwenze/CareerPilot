from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models import Resume, ResumeParseJob, User
from app.schemas.resume import ResumeStructuredData
from app.services.ai_client import AIClientError
from app.services.resume import process_resume_parse_job


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
                    "email": "zheng@example.com",
                    "phone": "17590522997",
                    "location": "北京",
                    "summary": "",
                },
                education=["新疆大学 软件工程 本科 2023.09 2027.06 211 双一流"],
                work_experience=[],
                projects=[
                    "黑马点评 高可用秒杀系统 完成高可用秒杀系统从0到1的架构设计与实现"
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
        "app.services.resume.extract_text_from_pdf_bytes",
        lambda _data: _raw_text(),
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
    assert persisted_resume.structured_json["projects"] == [
        "黑马点评 高可用秒杀系统 完成高可用秒杀系统从0到1的架构设计与实现。"
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
        "app.services.resume.extract_text_from_pdf_bytes",
        lambda _data: _raw_text(),
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
    assert persisted_job.status == "success"
    assert persisted_job.ai_status == "fallback_rule"
    assert persisted_job.ai_message == "AI 校准失败，已回退规则解析（模型返回格式非法）"
    assert job_count == 1


def _raw_text() -> str:
    return """
    郑文泽
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
) -> tuple[Resume, ResumeParseJob]:
    resume = Resume(
        id=uuid4(),
        user_id=user.id,
        file_name="resume.pdf",
        file_url="minio://career-pilot/resume.pdf",
        storage_bucket="career-pilot",
        storage_object_key=f"resumes/{user.id}/resume.pdf",
        content_type="application/pdf",
        file_size=1024,
        parse_status="pending",
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
