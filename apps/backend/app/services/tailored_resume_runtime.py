from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.tailored_resume import process_tailored_resume_workflow

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def resolve_session_factory(app: FastAPI) -> "async_sessionmaker[AsyncSession]":
    return getattr(app.state, "session_factory", get_session_factory())


async def run_tailored_resume_generation(
    app: FastAPI,
    *,
    session_id: UUID,
) -> None:
    settings = getattr(app.state, "settings", get_settings())
    await process_tailored_resume_workflow(
        session_id=session_id,
        session_factory=resolve_session_factory(app),
        settings=settings,
    )


def schedule_tailored_resume_generation(
    app: FastAPI,
    *,
    session_id: UUID,
) -> None:
    tasks: set[asyncio.Task[None]] = getattr(app.state, "tailored_resume_tasks", set())
    active_task_ids: set[UUID] = getattr(app.state, "tailored_resume_task_ids", set())
    app.state.tailored_resume_tasks = tasks
    app.state.tailored_resume_task_ids = active_task_ids

    if session_id in active_task_ids:
        return

    task = asyncio.create_task(run_tailored_resume_generation(app, session_id=session_id))
    tasks.add(task)
    active_task_ids.add(session_id)

    def _cleanup(finished_task: asyncio.Task[None]) -> None:
        tasks.discard(finished_task)
        active_task_ids.discard(session_id)

    task.add_done_callback(_cleanup)
