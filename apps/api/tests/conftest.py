from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.services.token_blocklist import InMemoryTokenBlocklist


@pytest.fixture
async def session_factory(tmp_path) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    database_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", future=True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory

    await engine.dispose()


@pytest.fixture
def app(session_factory: async_sessionmaker[AsyncSession]):
    application = create_app()
    application.state.token_blocklist = InMemoryTokenBlocklist()

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db_session] = override_get_db_session
    return application


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
