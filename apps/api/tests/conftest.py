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
from app.services.storage import StoredObject
from app.services.token_blocklist import InMemoryTokenBlocklist


class FakeObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def upload_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        self.objects[(bucket_name, object_key)] = data
        return StoredObject(bucket_name=bucket_name, object_key=object_key, etag="fake-etag")

    async def delete_object(self, *, bucket_name: str, object_key: str) -> None:
        self.objects.pop((bucket_name, object_key), None)

    async def get_download_url(
        self,
        *,
        bucket_name: str,
        object_key: str,
        expires_in_seconds: int,
    ) -> str:
        if (bucket_name, object_key) not in self.objects:
            raise FileNotFoundError(object_key)
        return f"https://fake-storage.local/{bucket_name}/{object_key}?expires={expires_in_seconds}"

    async def get_object_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> bytes:
        return self.objects[(bucket_name, object_key)]


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
    application.state.object_storage = FakeObjectStorage()
    application.state.session_factory = session_factory

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
