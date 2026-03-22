from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.schemas.resume import ResumeResponse
from app.services.resume import process_resume_parse_job
from app.services.storage import ObjectStorage

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

logger = logging.getLogger(__name__)


def should_schedule_resume_parse_job(resume: ResumeResponse) -> bool:
    parse_job = resume.latest_parse_job
    return (
        parse_job is not None
        and resume.parse_status in {"pending", "processing"}
        and parse_job.status in {"pending", "processing"}
    )


def resolve_session_factory(app: FastAPI) -> "async_sessionmaker[AsyncSession]":
    return getattr(app.state, "session_factory", get_session_factory())


def resolve_settings(app: FastAPI) -> Settings:
    return getattr(app.state, "settings", get_settings())


async def run_resume_parse_job(
    app: FastAPI,
    *,
    resume_id: UUID,
    parse_job_id: UUID,
    storage: ObjectStorage,
) -> None:
    try:
        await process_resume_parse_job(
            resume_id=resume_id,
            parse_job_id=parse_job_id,
            storage=storage,
            session_factory=resolve_session_factory(app),
            settings=resolve_settings(app),
        )
    except Exception:
        logger.exception(
            "Resume parse background job crashed: resume_id=%s parse_job_id=%s",
            resume_id,
            parse_job_id,
        )


def schedule_resume_parse_job(
    app: FastAPI,
    *,
    resume_id: UUID,
    parse_job_id: UUID,
    storage: ObjectStorage,
) -> None:
    tasks: set[asyncio.Task[None]] = getattr(app.state, "resume_parse_tasks", set())
    active_task_ids: set[UUID] = getattr(app.state, "resume_parse_task_ids", set())
    app.state.resume_parse_tasks = tasks
    app.state.resume_parse_task_ids = active_task_ids

    if parse_job_id in active_task_ids:
        return

    task = asyncio.create_task(
        run_resume_parse_job(
            app,
            resume_id=resume_id,
            parse_job_id=parse_job_id,
            storage=storage,
        )
    )
    tasks.add(task)
    active_task_ids.add(parse_job_id)

    def _cleanup(finished_task: asyncio.Task[None]) -> None:
        tasks.discard(finished_task)
        active_task_ids.discard(parse_job_id)

    task.add_done_callback(_cleanup)


def ensure_resume_parse_job_scheduled(
    app: FastAPI,
    *,
    resume: ResumeResponse,
    storage: ObjectStorage,
) -> None:
    if not should_schedule_resume_parse_job(resume):
        return

    parse_job = resume.latest_parse_job
    assert parse_job is not None
    schedule_resume_parse_job(
        app,
        resume_id=resume.id,
        parse_job_id=parse_job.id,
        storage=storage,
    )
