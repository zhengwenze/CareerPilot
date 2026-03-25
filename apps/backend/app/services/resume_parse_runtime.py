from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import FastAPI

from app.core.config import Settings
from app.db.session import get_session_factory
from app.services.resume import process_resume_parse_job
from app.services.storage import ObjectStorage

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


def resolve_session_factory(app: FastAPI) -> "async_sessionmaker[AsyncSession]":
    return getattr(app.state, "session_factory", get_session_factory())


def resolve_settings(app: FastAPI) -> Settings | None:
    return getattr(app.state, "settings", None)


async def run_resume_parse_job(
    app: FastAPI,
    *,
    resume_id: UUID,
    parse_job_id: UUID,
    storage: ObjectStorage,
) -> None:
    await process_resume_parse_job(
        resume_id=resume_id,
        parse_job_id=parse_job_id,
        storage=storage,
        session_factory=resolve_session_factory(app),
        settings=resolve_settings(app),
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
        if finished_task.cancelled():
            logger.warning("resume parse task cancelled parse_job_id=%s", parse_job_id)
            return
        exc = finished_task.exception()
        if exc is not None:
            logger.exception(
                "resume parse task failed parse_job_id=%s",
                parse_job_id,
                exc_info=exc,
            )

    task.add_done_callback(_cleanup)
