"""
Unit tests for domain/portfolio.py.

Tests portfolio domain helpers in isolation:
- generate_s3_key (pure function — no DB needed)
- compute_is_verified (DB-taking — uses in-memory SQLite)
"""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-chars-long!")
os.environ.setdefault("API_KEY", "test-api-key-minimum-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import re
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.portfolio import compute_is_verified, generate_s3_key
from src.infra.database import Base
from src.infra.models import GigModel, UserModel

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# generate_s3_key
# ---------------------------------------------------------------------------


class TestGenerateS3Key:
    def test_key_starts_with_portfolio_prefix(self):
        user_id = str(uuid.uuid4())
        key = generate_s3_key(user_id, "myfile.png")
        assert key.startswith(f"portfolio/{user_id}/")

    def test_key_ends_with_sanitized_filename(self):
        user_id = str(uuid.uuid4())
        key = generate_s3_key(user_id, "my file.png")
        # spaces replaced with underscore
        assert key.endswith("my_file.png")

    def test_key_contains_uuid_segment(self):
        user_id = str(uuid.uuid4())
        key = generate_s3_key(user_id, "photo.jpg")
        # key format: portfolio/{user_id}/{uuid}-{filename}
        parts = key.split("/")
        assert len(parts) == 3
        uuid_and_name = parts[2]
        uuid_part = uuid_and_name.split("-photo.jpg")[0]
        # Should be a valid UUID
        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            uuid_part,
        )

    def test_sanitizes_path_traversal(self):
        user_id = str(uuid.uuid4())
        key = generate_s3_key(user_id, "../../../etc/passwd")
        assert ".." not in key
        assert "etc" in key or "passwd" in key  # name preserved, dots replaced

    def test_different_calls_produce_different_keys(self):
        user_id = str(uuid.uuid4())
        k1 = generate_s3_key(user_id, "file.pdf")
        k2 = generate_s3_key(user_id, "file.pdf")
        assert k1 != k2


# ---------------------------------------------------------------------------
# compute_is_verified
# ---------------------------------------------------------------------------


class TestComputeIsVerified:
    @pytest.mark.asyncio
    async def test_none_gig_id_returns_false(self, db_session: AsyncSession):
        result = await compute_is_verified(db_session, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_string_gig_id_returns_false(self, db_session: AsyncSession):
        result = await compute_is_verified(db_session, "")
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_gig_returns_false(self, db_session: AsyncSession):
        # Gig with this ID doesn't exist
        result = await compute_is_verified(db_session, str(uuid.uuid4()))
        assert result is False

    @pytest.mark.asyncio
    async def test_completed_gig_returns_true(self, db_session: AsyncSession):
        # Create a user first (gig FK references users.id)
        user = UserModel(
            name="Alice",
            role="USER_ROLE_CLIENT",
            status="USER_STATUS_ACTIVE",
        )
        db_session.add(user)
        await db_session.flush()

        gig = GigModel(
            client_id=user.id,
            title="Test Gig",
            description="A test gig",
            total_amount="1000000000000000000",
            status="GIG_STATUS_COMPLETED",
        )
        db_session.add(gig)
        await db_session.flush()

        result = await compute_is_verified(db_session, gig.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_in_progress_gig_returns_false(self, db_session: AsyncSession):
        user = UserModel(
            name="Bob",
            role="USER_ROLE_CLIENT",
            status="USER_STATUS_ACTIVE",
        )
        db_session.add(user)
        await db_session.flush()

        gig = GigModel(
            client_id=user.id,
            title="Active Gig",
            description="A gig in progress",
            total_amount="500000000000000000",
            status="GIG_STATUS_IN_PROGRESS",
        )
        db_session.add(gig)
        await db_session.flush()

        result = await compute_is_verified(db_session, gig.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_draft_gig_returns_false(self, db_session: AsyncSession):
        user = UserModel(
            name="Carol",
            role="USER_ROLE_CLIENT",
            status="USER_STATUS_ACTIVE",
        )
        db_session.add(user)
        await db_session.flush()

        gig = GigModel(
            client_id=user.id,
            title="Draft Gig",
            description="A draft gig",
            total_amount="500000000000000000",
            status="GIG_STATUS_DRAFT",
        )
        db_session.add(gig)
        await db_session.flush()

        result = await compute_is_verified(db_session, gig.id)
        assert result is False
