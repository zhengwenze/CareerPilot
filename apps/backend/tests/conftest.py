from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings
from app.core.security import create_access_token
from app.db.base import Base
from app.main import create_app
from app.models import User
from app.routers.deps import get_db_session


class FakeObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def upload_bytes(self, *, bucket_name: str, object_key: str, data: bytes, content_type: str):
        del content_type
        self.objects[(bucket_name, object_key)] = data
        return type(
            "StoredObject",
            (),
            {"bucket_name": bucket_name, "object_key": object_key, "etag": "fake"},
        )()

    async def delete_object(self, *, bucket_name: str, object_key: str) -> None:
        self.objects.pop((bucket_name, object_key), None)

    async def get_download_url(self, *, bucket_name: str, object_key: str, expires_in_seconds: int) -> str:
        del expires_in_seconds
        return f"https://example.test/{bucket_name}/{object_key}"

    async def get_object_bytes(self, *, bucket_name: str, object_key: str) -> bytes:
        return self.objects[(bucket_name, object_key)]


@pytest_asyncio.fixture
async def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    settings = Settings(
        app_env="test",
        database_url=database_url,
        alembic_database_url=f"sqlite:///{db_path}",
        storage_provider="test",
        redis_url=None,
    )
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    application = create_app(settings)
    application.state.object_storage = FakeObjectStorage()
    application.state.session_factory = session_factory

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db_session] = override_get_db_session

    monkeypatch.setattr("app.routers.resumes.schedule_resume_parse_job", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.routers.jobs.schedule_job_parse_job", lambda *args, **kwargs: None)

    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest_asyncio.fixture
async def db_session(app) -> AsyncGenerator[AsyncSession, None]:
    session_factory = app.state.session_factory
    async with session_factory() as session:
        yield session


async def create_test_user(
    session: AsyncSession,
    *,
    email: str,
) -> tuple[User, str]:
    from app.services.auth import register_user

    user = await register_user(session, email=email, password="password123", nickname=email.split("@")[0])
    token, _ = create_access_token(str(user.id))
    return user, token


@pytest.fixture
def pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
