from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.models import JobDescription, Resume, User
from app.schemas.tailored_resume import (
    TailoredResumeGenerateFromSavedJobRequest,
    TailoredResumeWorkflowResponse,
)
from app.services.tailored_resume import generate_tailored_resume_for_saved_job
from app.services.tailored_resume_runtime import schedule_tailored_resume_generation

ACTIVE_AUTOSTART_STATUSES = {"idle", "processing", "segment_progress"}


def resolve_session_factory(app: FastAPI) -> async_sessionmaker[AsyncSession]:
    return getattr(app.state, "session_factory", get_session_factory())


def resolve_settings(app: FastAPI) -> Settings:
    return getattr(app.state, "settings", get_settings())


def _extract_resume_markdown(resume: Resume) -> str:
    artifacts = resume.parse_artifacts_json or {}
    return str(artifacts.get("canonical_resume_md") or resume.raw_text or "").strip()


async def maybe_autostart_tailored_resume(
    app: FastAPI,
    *,
    user_id: UUID,
    resume_id: UUID,
    job_id: UUID,
) -> TailoredResumeWorkflowResponse | None:
    session_factory = resolve_session_factory(app)
    settings = resolve_settings(app)

    async with session_factory() as session:
        current_user = await session.get(User, user_id)
        resume = await session.get(Resume, resume_id)
        job = await session.get(JobDescription, job_id)
        if current_user is None or resume is None or job is None:
            return None
        if resume.user_id != current_user.id or job.user_id != current_user.id:
            return None
        if resume.parse_status != "success" or not _extract_resume_markdown(resume):
            return None
        if job.parse_status != "success" or not job.structured_json:
            return None

        workflow = await generate_tailored_resume_for_saved_job(
            session,
            current_user=current_user,
            payload=TailoredResumeGenerateFromSavedJobRequest(
                resume_id=resume.id,
                job_id=job.id,
                force_refresh=False,
            ),
            session_factory=session_factory,
            settings=settings,
        )

    if workflow.tailored_resume.display_status in ACTIVE_AUTOSTART_STATUSES:
        schedule_tailored_resume_generation(
            app,
            session_id=workflow.tailored_resume.session_id,
        )
    return workflow


async def maybe_autostart_tailored_resume_for_job(
    app: FastAPI,
    *,
    job_id: UUID,
) -> TailoredResumeWorkflowResponse | None:
    async with resolve_session_factory(app)() as session:
        job = await session.get(JobDescription, job_id)
        if job is None or job.recommended_resume_id is None:
            return None
        user_id = job.user_id
        resume_id = job.recommended_resume_id

    return await maybe_autostart_tailored_resume(
        app,
        user_id=user_id,
        resume_id=resume_id,
        job_id=job_id,
    )
