from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.mock_interview import (
    process_mock_interview_prep,
    process_mock_interview_turn,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def resolve_session_factory(app: FastAPI) -> "async_sessionmaker[AsyncSession]":
    return getattr(app.state, "session_factory", get_session_factory())


async def run_mock_interview_prep(app: FastAPI, *, session_id: UUID) -> None:
    await process_mock_interview_prep(
        session_id=session_id,
        session_factory=resolve_session_factory(app),
        settings=getattr(app.state, "settings", get_settings()),
    )


async def run_mock_interview_turn(app: FastAPI, *, session_id: UUID, turn_id: UUID) -> None:
    await process_mock_interview_turn(
        session_id=session_id,
        turn_id=turn_id,
        session_factory=resolve_session_factory(app),
        settings=getattr(app.state, "settings", get_settings()),
    )


def _schedule_task(
    app: FastAPI,
    *,
    key: str,
    coroutine_factory,
) -> None:
    tasks: set[asyncio.Task[None]] = getattr(app.state, "mock_interview_tasks", set())
    active_task_ids: set[str] = getattr(app.state, "mock_interview_task_ids", set())
    app.state.mock_interview_tasks = tasks
    app.state.mock_interview_task_ids = active_task_ids

    if key in active_task_ids:
        return

    task = asyncio.create_task(coroutine_factory())
    tasks.add(task)
    active_task_ids.add(key)

    def _cleanup(finished_task: asyncio.Task[None]) -> None:
        tasks.discard(finished_task)
        active_task_ids.discard(key)

    task.add_done_callback(_cleanup)


def schedule_mock_interview_prep(app: FastAPI, *, session_id: UUID) -> None:
    _schedule_task(
        app,
        key=f"prep:{session_id}",
        coroutine_factory=lambda: run_mock_interview_prep(app, session_id=session_id),
    )


def schedule_mock_interview_turn(app: FastAPI, *, session_id: UUID, turn_id: UUID) -> None:
    _schedule_task(
        app,
        key=f"turn:{session_id}:{turn_id}",
        coroutine_factory=lambda: run_mock_interview_turn(
            app,
            session_id=session_id,
            turn_id=turn_id,
        ),
    )
