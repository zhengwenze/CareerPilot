from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import FastAPI

from app.db.session import get_session_factory
from app.services.resume import process_resume_parse_job
from app.services.storage import ObjectStorage

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def resolve_session_factory(app: FastAPI) -> "async_sessionmaker[AsyncSession]":
    return getattr(app.state, "session_factory", get_session_factory())


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
