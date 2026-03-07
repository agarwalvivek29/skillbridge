"""
E2E test fixtures.

Uses an in-memory SQLite database (via aiosqlite) so e2e tests don't require
a running PostgreSQL instance. The FastAPI test client uses httpx with ASGI transport.
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.infra.database import get_session
from api.infra.models import Base
from api.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

TEST_JWT_SECRET = "test-secret-that-is-at-least-32-characters-long"
TEST_API_KEY = "test-api-key-16ch"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, monkeypatch):
    """
    AsyncClient wired to the FastAPI app with:
    - in-memory SQLite DB (overriding the real session)
    - test JWT_SECRET and API_KEY
    """
    monkeypatch.setattr("api.config.settings.jwt_secret", TEST_JWT_SECRET)
    monkeypatch.setattr("api.config.settings.api_key", TEST_API_KEY)
    monkeypatch.setattr("api.config.settings.siwe_domain", "localhost")
    monkeypatch.setattr("api.config.settings.siwe_chain_id", 84532)
    monkeypatch.setattr("api.config.settings.nonce_ttl_seconds", 300)
    monkeypatch.setattr("api.main.settings.jwt_secret", TEST_JWT_SECRET)
    monkeypatch.setattr("api.main.settings.api_key", TEST_API_KEY)

    async def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
